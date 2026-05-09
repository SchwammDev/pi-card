import argparse
import time
import urllib.request
import wave
from pathlib import Path

import numpy as np

DEFAULT_BACKBONE = "neuphonic/neutts-air-q4-gguf"
DEFAULT_CODEC = "neuphonic/neucodec-onnx-decoder"
DEFAULT_OUTPUT_DIR = Path("/tmp/pi-card-neutts-probe")
DEFAULT_SAMPLE_DIR = Path.home() / ".local" / "share" / "pi-card" / "neutts-samples"

REF_VOICE_NAME = "jo"
REF_CODES_URL = f"https://github.com/neuphonic/neutts/raw/main/samples/{REF_VOICE_NAME}.pt"
REF_TEXT_URL = f"https://raw.githubusercontent.com/neuphonic/neutts/main/samples/{REF_VOICE_NAME}.txt"

LONG_SENTENCE = (
    "Once upon a time, in a quiet little garden tucked between two old "
    "stone houses, a curious robot named Pip discovered the gentle art "
    "of patience while waiting for tomatoes to ripen on the vine."
)

SHORT_SENTENCE = "Four."


def main() -> None:
    args = _parse_args()

    ref_codes_path = _ensure_reference(args.sample_dir / f"{REF_VOICE_NAME}.pt", REF_CODES_URL)
    ref_text_path = _ensure_reference(args.sample_dir / f"{REF_VOICE_NAME}.txt", REF_TEXT_URL)

    print(f"Backbone: {args.backbone}")
    print(f"Codec:    {args.codec}")
    print(f"Reference voice: {ref_codes_path.name}")
    print()
    print("Loading model (first run downloads from HuggingFace)...")
    tts = _load_tts(args.backbone, args.codec)
    print(f"Model loaded. sample_rate={tts.sample_rate}")
    print()

    import torch

    ref_codes = torch.load(ref_codes_path)
    ref_text = ref_text_path.read_text(encoding="utf-8").strip()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    sentences = [args.text] if args.text else [LONG_SENTENCE, SHORT_SENTENCE]
    for sentence in sentences:
        label = "long" if len(sentence) > 50 else "short"
        _measure_one(tts, sentence, label, ref_codes, ref_text, args.output_dir)
        print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="probe_neutts_streaming")
    parser.add_argument("--backbone", default=DEFAULT_BACKBONE)
    parser.add_argument("--codec", default=DEFAULT_CODEC)
    parser.add_argument("--text", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE_DIR)
    return parser.parse_args()


def _ensure_reference(local_path: Path, url: str) -> Path:
    if local_path.exists():
        return local_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {local_path}")
    urllib.request.urlretrieve(url, local_path)
    return local_path


def _load_tts(backbone: str, codec: str):
    from neutts import NeuTTS

    return NeuTTS(
        backbone_repo=backbone,
        backbone_device="cpu",
        codec_repo=codec,
        codec_device="cpu",
    )


def _measure_one(tts, sentence: str, label: str, ref_codes, ref_text: str, output_dir: Path) -> None:
    print(f"--- {label} ({len(sentence)} chars) ---")
    print(f"text: {sentence!r}")
    print()
    print(f"{'idx':>3}  {'arrival_s':>10}  {'gap_s':>8}  {'audio_s':>8}  {'samples':>9}")
    print("-" * 55)

    start = time.perf_counter()
    last = start
    chunks: list[np.ndarray] = []
    first_arrival_s = None

    for idx, chunk in enumerate(tts.infer_stream(sentence, ref_codes, ref_text)):
        now = time.perf_counter()
        if first_arrival_s is None:
            first_arrival_s = now - start
        audio_int16 = (chunk * 32767).astype(np.int16)
        audio_s = audio_int16.shape[0] / tts.sample_rate
        chunks.append(audio_int16)
        print(
            f"{idx:>3}  {now - start:>10.3f}  {now - last:>8.3f}  "
            f"{audio_s:>8.3f}  {audio_int16.shape[0]:>9}"
        )
        last = now

    total_s = time.perf_counter() - start

    if not chunks:
        print("no chunks emitted")
        return

    full_audio = np.concatenate(chunks)
    total_audio_s = full_audio.shape[0] / tts.sample_rate
    out_path = output_dir / f"probe_{label}.wav"
    _write_wav(out_path, full_audio, tts.sample_rate)

    print()
    print(f"chunks:                 {len(chunks)}")
    print(f"first chunk arrived at: {first_arrival_s:.3f} s   <-- TTFA")
    print(f"total wall time:        {total_s:.3f} s")
    print(f"total audio duration:   {total_audio_s:.3f} s")
    print(f"RTF (wall / audio):     {total_s / total_audio_s:.2f}")
    print(f"saved to:               {out_path}")
    print(f"verdict: {_verdict(first_arrival_s, total_s, total_audio_s)}")


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(samples.tobytes())


def _verdict(ttfa_s: float, total_s: float, audio_s: float) -> str:
    if ttfa_s < 0.5:
        return "EXCELLENT: TTFA < 0.5 s, ship-worthy if fidelity holds"
    if ttfa_s < 1.0:
        return "GOOD: TTFA under 1 s, likely a clear win over current Piper"
    if ttfa_s < 2.0:
        return "MARGINAL: TTFA between 1-2 s, compare to Piper-medium 4 s on long sentences"
    return "POOR: TTFA > 2 s, NeuTTS Air on this CPU may not beat Piper"


if __name__ == "__main__":
    main()
