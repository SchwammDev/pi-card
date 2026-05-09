import argparse
import time
from pathlib import Path

DEFAULT_VOICE_NAME = "en_GB-jenny_dioco-medium"
DEFAULT_VOICE_DIR = Path.home() / ".local/share/pi-card/voices"
BYTES_PER_SAMPLE = 2

LONG_SENTENCE = (
    "Once upon a time, in a quiet little garden tucked between two old "
    "stone houses, a curious robot named Pip discovered the gentle art "
    "of patience while waiting for tomatoes to ripen on the vine."
)

SHORT_SENTENCE = "Four."


def main() -> None:
    args = _parse_args()
    voice = _load_voice(args.voice, args.voice_dir)
    sample_rate = int(voice.config.sample_rate)

    sentences = [args.text] if args.text else [LONG_SENTENCE, SHORT_SENTENCE]
    for sentence in sentences:
        _measure_sentence(voice, sentence, sample_rate)
        print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="measure_piper_chunks",
        description=(
            "Time the per-chunk arrival of Piper's synthesize() iterator "
            "to decide whether sub-sentence streaming is feasible."
        ),
    )
    parser.add_argument("--voice", default=DEFAULT_VOICE_NAME)
    parser.add_argument("--voice-dir", type=Path, default=DEFAULT_VOICE_DIR)
    parser.add_argument(
        "--text",
        default=None,
        help="Single sentence to synthesise (overrides the built-in long+short pair).",
    )
    return parser.parse_args()


def _load_voice(voice_name: str, voice_dir: Path):
    from piper.download_voices import download_voice
    from piper.voice import PiperVoice

    voice_dir.mkdir(parents=True, exist_ok=True)
    model_path = voice_dir / f"{voice_name}.onnx"
    if not model_path.exists():
        download_voice(voice_name, voice_dir)
    return PiperVoice.load(model_path)


def _measure_sentence(voice, sentence: str, sample_rate: int) -> None:
    print(f"sentence ({len(sentence)} chars): {sentence!r}")
    print(f"sample_rate: {sample_rate} Hz")
    print()
    print(f"{'idx':>3}  {'arrival_s':>10}  {'gap_s':>8}  {'audio_s':>8}  {'bytes':>9}")
    print("-" * 50)

    start = time.perf_counter()
    last = start
    total_audio_s = 0.0
    chunk_count = 0
    first_arrival_s = None

    for idx, chunk in enumerate(voice.synthesize(sentence)):
        now = time.perf_counter()
        audio = bytes(chunk.audio_int16_bytes)
        audio_s = len(audio) / (sample_rate * BYTES_PER_SAMPLE)
        total_audio_s += audio_s
        if first_arrival_s is None:
            first_arrival_s = now - start
        print(
            f"{idx:>3}  {now - start:>10.3f}  {now - last:>8.3f}  "
            f"{audio_s:>8.3f}  {len(audio):>9}"
        )
        last = now
        chunk_count += 1

    total_s = time.perf_counter() - start

    print()
    print(f"chunks: {chunk_count}")
    print(f"first chunk arrived at: {first_arrival_s:.3f} s" if chunk_count else "no chunks")
    print(f"total wall time:        {total_s:.3f} s")
    print(f"total audio duration:   {total_audio_s:.3f} s")
    print(f"verdict: {_verdict(chunk_count, first_arrival_s, total_s)}")


def _verdict(chunk_count: int, first_arrival_s: float | None, total_s: float) -> str:
    if chunk_count == 0:
        return "no chunks emitted"
    if chunk_count == 1:
        return "SENTENCE-LEVEL: one chunk per sentence; sub-sentence streaming not exposed"
    if first_arrival_s is not None and first_arrival_s < 0.5 * total_s:
        return "SUB-SENTENCE: first chunk arrives well before synth completes; streaming wins"
    return "MIXED: multiple chunks, but first arrives late; check gap_s column"


if __name__ == "__main__":
    main()
