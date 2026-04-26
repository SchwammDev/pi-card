import argparse
import logging
import logging.handlers
import sys
from dataclasses import replace
from pathlib import Path

from pi_card.assistant import VoiceAssistant
from pi_card.config import Config

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "pi-card" / "config.yaml"
DEFAULT_LOG_DIR = Path.home() / ".local" / "state" / "pi-card" / "logs"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5

TRANSCRIPTS_LOGGER_NAME = "pi_card.transcripts"

EN_VOICE = "en_GB-alan-medium"
FR_VOICE = "fr_FR-siwis-medium"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pi-card",
        description="Raspberry Pi voice assistant.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to config.yaml (default: {DEFAULT_CONFIG_PATH}).",
    )
    parser.add_argument(
        "--language",
        choices=["en", "fr"],
        default=None,
        help="Override the starting language from config.",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Root log level for errors.log (default: WARNING).",
    )
    parser.add_argument(
        "--debug-transcripts",
        action="store_true",
        help="Write user and assistant turns to transcripts.log.",
    )
    return parser.parse_args(argv)


def load_config_with_overrides(path: Path, *, language: str | None) -> Config:
    config = Config.load(path)
    if language is not None:
        config = replace(config, language=language)
    return config


def configure_logging(
    *,
    log_dir: Path = DEFAULT_LOG_DIR,
    level: str = "WARNING",
    debug_transcripts: bool = False,
) -> None:
    """Configure rotating file logging per Project_Overview.

    Idempotent: clears our own handlers before re-adding so the CLI can be
    invoked multiple times in one process (notably, in tests)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    root = logging.getLogger()
    _remove_rotating_file_handlers(root)
    _remove_stderr_stream_handlers(root)
    root.setLevel(level)
    errors_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    errors_handler.setFormatter(formatter)
    root.addHandler(errors_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    transcripts = logging.getLogger(TRANSCRIPTS_LOGGER_NAME)
    _remove_rotating_file_handlers(transcripts)
    if debug_transcripts:
        transcripts.setLevel(logging.INFO)
        transcripts.propagate = False  # keep transcripts out of errors.log
        transcripts_handler = logging.handlers.RotatingFileHandler(
            log_dir / "transcripts.log",
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
        )
        transcripts_handler.setFormatter(formatter)
        transcripts.addHandler(transcripts_handler)
    else:
        transcripts.setLevel(logging.WARNING)
        transcripts.propagate = False


def _remove_rotating_file_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()


def _remove_stderr_stream_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if (
            isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.handlers.RotatingFileHandler)
            and getattr(handler, "stream", None) is sys.stderr
        ):
            logger.removeHandler(handler)


def build_assistant(config: Config) -> VoiceAssistant:
    """Construct the production assistant with real hardware adapters.

    Imports are local so that test environments (and --help) don't need
    hardware libraries installed."""
    from pi_card.adapters.openai_agent import OpenAIAgent, load_openai_client
    from pi_card.adapters.respeaker_input import ReSpeakerInput
    from pi_card.adapters.respeaker_leds import ReSpeakerLEDs
    from pi_card.adapters.usb_speaker import USBSpeakerOutput
    from pi_card.pipeline.stt import WhisperSTT, load_faster_whisper_model
    from pi_card.pipeline.tts import PiperTTS, load_piper_voice
    from pi_card.pipeline.wake_word import WakeWordDetector, load_openwakeword_engine

    client = load_openai_client(base_url=config.base_url, api_key=config.api_key)

    return VoiceAssistant(
        audio_in=ReSpeakerInput(),
        audio_out=USBSpeakerOutput(),
        leds=ReSpeakerLEDs(),
        agent=OpenAIAgent(client=client, model=config.model),
        wake_word_detector=WakeWordDetector(engine=load_openwakeword_engine()),
        stt=WhisperSTT(model=load_faster_whisper_model()),
        tts_by_language={
            "en": PiperTTS(voice=load_piper_voice(EN_VOICE)),
            "fr": PiperTTS(voice=load_piper_voice(FR_VOICE)),
        },
        language=config.language,
        silence_timeout=config.silence_timeout,
        max_stt_retries=config.max_stt_retries,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(level=args.log_level, debug_transcripts=args.debug_transcripts)
    config = load_config_with_overrides(args.config, language=args.language)

    logger = logging.getLogger(__name__)
    logger.info("pi-card starting (language=%s, model=%s)", config.language, config.model)

    assistant = build_assistant(config)
    try:
        assistant.run()
    except KeyboardInterrupt:
        logger.info("pi-card stopped by user")
    return 0
