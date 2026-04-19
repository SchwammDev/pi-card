import logging
import logging.handlers
import textwrap
from pathlib import Path

import pytest

from pi_card import cli


@pytest.fixture
def isolated_logging():
    """Snapshot and restore logging state so each test gets a clean slate."""
    root = logging.getLogger()
    before_root = (root.level, list(root.handlers))

    transcripts = logging.getLogger(cli.TRANSCRIPTS_LOGGER_NAME)
    before_transcripts = (
        transcripts.level,
        transcripts.propagate,
        list(transcripts.handlers),
    )
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.setLevel(before_root[0])
    for handler in before_root[1]:
        root.addHandler(handler)

    for handler in list(transcripts.handlers):
        transcripts.removeHandler(handler)
        handler.close()
    transcripts.setLevel(before_transcripts[0])
    transcripts.propagate = before_transcripts[1]
    for handler in before_transcripts[2]:
        transcripts.addHandler(handler)


def _valid_config(tmp_path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        textwrap.dedent(
            """
            agent:
              base_url: https://api.example.com/v1
              api_key: secret
              model: gpt-4o-mini
            """
        )
    )
    return path


def test_parse_args_uses_documented_defaults():
    args = cli.parse_args([])
    assert args.config == cli.DEFAULT_CONFIG_PATH
    assert args.language is None
    assert args.log_level == "WARNING"
    assert args.debug_transcripts is False


def test_parse_args_reads_every_documented_flag(tmp_path):
    alt = tmp_path / "alt.yaml"
    args = cli.parse_args(
        [
            "--config",
            str(alt),
            "--language",
            "fr",
            "--log-level",
            "DEBUG",
            "--debug-transcripts",
        ]
    )
    assert args.config == alt
    assert args.language == "fr"
    assert args.log_level == "DEBUG"
    assert args.debug_transcripts is True


def test_language_cli_flag_overrides_config(tmp_path):
    base = cli.load_config_with_overrides(_valid_config(tmp_path), language=None)
    overridden = cli.load_config_with_overrides(
        _valid_config(tmp_path), language="fr"
    )
    assert base.language == "en"
    assert overridden.language == "fr"


def test_configure_logging_writes_errors_log_always(tmp_path, isolated_logging):
    cli.configure_logging(log_dir=tmp_path, level="INFO", debug_transcripts=False)
    logging.getLogger("pi_card.something").error("boom")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert (tmp_path / "errors.log").exists()
    assert "boom" in (tmp_path / "errors.log").read_text()
    assert not (tmp_path / "transcripts.log").exists()


def test_configure_logging_writes_transcripts_log_when_enabled(
    tmp_path, isolated_logging
):
    cli.configure_logging(log_dir=tmp_path, level="INFO", debug_transcripts=True)
    logging.getLogger(cli.TRANSCRIPTS_LOGGER_NAME).info("user: hello")
    for handler in logging.getLogger(cli.TRANSCRIPTS_LOGGER_NAME).handlers:
        handler.flush()

    assert (tmp_path / "transcripts.log").exists()
    assert "user: hello" in (tmp_path / "transcripts.log").read_text()


def test_transcripts_do_not_leak_into_errors_log(tmp_path, isolated_logging):
    cli.configure_logging(log_dir=tmp_path, level="INFO", debug_transcripts=True)
    logging.getLogger(cli.TRANSCRIPTS_LOGGER_NAME).info("user: secret")
    for handler in (
        logging.getLogger().handlers
        + logging.getLogger(cli.TRANSCRIPTS_LOGGER_NAME).handlers
    ):
        handler.flush()

    errors_text = (tmp_path / "errors.log").read_text() if (tmp_path / "errors.log").exists() else ""
    assert "secret" not in errors_text


def test_configure_logging_is_idempotent(tmp_path, isolated_logging):
    cli.configure_logging(log_dir=tmp_path, level="INFO", debug_transcripts=False)
    cli.configure_logging(log_dir=tmp_path, level="INFO", debug_transcripts=True)

    root_file_handlers = [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    transcripts_file_handlers = [
        h
        for h in logging.getLogger(cli.TRANSCRIPTS_LOGGER_NAME).handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(root_file_handlers) == 1
    assert len(transcripts_file_handlers) == 1
