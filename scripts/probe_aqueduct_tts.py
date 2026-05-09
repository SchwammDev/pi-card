import argparse
import time
from pathlib import Path

from pi_card.config import Config

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "pi-card" / "config.yaml"
DEFAULT_OUTPUT_DIR = Path("/tmp/pi-card-tts-probe")

LONG_SENTENCE = (
    "Once upon a time, in a quiet little garden tucked between two old "
    "stone houses, a curious robot named Pip discovered the gentle art "
    "of patience while waiting for tomatoes to ripen on the vine."
)

SHORT_SENTENCE = "Four."


def main() -> None:
    args = _parse_args()
    config = Config.load(args.config)
    client = _build_client(config)

    print(f"Aqueduct base_url: {config.base_url}")
    print()

    _print_model_list(client, args.filter)

    if not args.model:
        print()
        print("To attempt synthesis, re-run with --model <id> [--voice <name>]")
        print("(pick a model id from the list above)")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print()
    print(f"Attempting /audio/speech with model={args.model!r} voice={args.voice!r}")
    print(f"Output dir: {args.output_dir}")
    print()
    for label, text in [("long", LONG_SENTENCE), ("short", SHORT_SENTENCE)]:
        _measure_one(client, args.model, args.voice, args.response_format, label, text, args.output_dir)
        print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="probe_aqueduct_tts")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--filter",
        default=None,
        help="Only list models whose id contains this substring (case-insensitive).",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--response-format", default=None, help="e.g. wav, mp3, pcm.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def _build_client(config: Config):
    from openai import OpenAI

    return OpenAI(base_url=config.base_url, api_key=config.api_key)


def _print_model_list(client, name_filter: str | None) -> None:
    print("Available models:")
    try:
        response = client.models.list()
    except Exception as exc:
        print(f"  ERROR listing models: {type(exc).__name__}: {exc}")
        return

    needle = name_filter.lower() if name_filter else None
    shown = 0
    for model in response.data:
        mid = getattr(model, "id", str(model))
        if needle and needle not in mid.lower():
            continue
        print(f"  - {mid}")
        shown += 1
    if shown == 0:
        print("  (no models matched)" if needle else "  (empty)")


def _measure_one(client, model, voice, response_format, label, text, output_dir):
    suffix = response_format or "bin"
    out_path = output_dir / f"probe_{label}.{suffix}"

    print(f"--- {label} ({len(text)} chars) ---")
    print(f"text: {text!r}")

    kwargs = {"model": model, "input": text}
    if voice is not None:
        kwargs["voice"] = voice
    if response_format is not None:
        kwargs["response_format"] = response_format

    start = time.perf_counter()
    ttfb_s = None
    chunks: list[bytes] = []

    try:
        with client.audio.speech.with_streaming_response.create(**kwargs) as response:
            for chunk in response.iter_bytes(chunk_size=4096):
                if chunk and ttfb_s is None:
                    ttfb_s = time.perf_counter() - start
                if chunk:
                    chunks.append(chunk)
    except Exception as exc:
        print(f"  ERROR: {type(exc).__name__}: {exc}")
        return

    total_s = time.perf_counter() - start
    body = b"".join(chunks)
    out_path.write_bytes(body)

    print(f"  TTFB:           {ttfb_s:.3f} s" if ttfb_s is not None else "  TTFB: (no bytes)")
    print(f"  total wall:     {total_s:.3f} s")
    print(f"  bytes:          {len(body)}")
    print(f"  saved to:       {out_path}")


if __name__ == "__main__":
    main()
