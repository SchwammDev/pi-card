from typing import Iterable, Iterator

TERMINAL_PUNCTUATION = ".?!…"
MIN_CHUNK_CHARS = 5


def chunk_sentences(deltas: Iterable[str]) -> Iterator[str]:
    buffer = ""
    for delta in deltas:
        buffer += delta
        while True:
            split_at = _find_split_point(buffer)
            if split_at is None:
                break
            chunk = buffer[:split_at].strip()
            buffer = buffer[split_at:].lstrip()
            if chunk:
                yield chunk
    tail = buffer.strip()
    if tail:
        yield tail


def _find_split_point(buffer: str) -> int | None:
    for i in range(len(buffer) - 1):
        if buffer[i] in TERMINAL_PUNCTUATION and buffer[i + 1].isspace():
            if len(buffer[: i + 1].strip()) >= MIN_CHUNK_CHARS:
                return i + 1
    return None
