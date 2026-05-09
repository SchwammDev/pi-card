from typing import Iterable, Iterator

TERMINAL_PUNCTUATION = ".?!…"
FIRST_CHUNK_PUNCTUATION = TERMINAL_PUNCTUATION + ","
MIN_CHUNK_CHARS = 5


def chunk_sentences(deltas: Iterable[str]) -> Iterator[str]:
    buffer = ""
    first_chunk_pending = True
    for delta in deltas:
        buffer += delta
        while True:
            split_at = _find_split_point(buffer, allow_comma=first_chunk_pending)
            if split_at is None:
                break
            chunk = buffer[:split_at].strip()
            buffer = buffer[split_at:].lstrip()
            if chunk:
                yield chunk
                first_chunk_pending = False
    tail = buffer.strip()
    if tail:
        yield tail


def _find_split_point(buffer: str, *, allow_comma: bool) -> int | None:
    split_chars = FIRST_CHUNK_PUNCTUATION if allow_comma else TERMINAL_PUNCTUATION
    for i in range(len(buffer) - 1):
        if buffer[i] in split_chars and buffer[i + 1].isspace():
            if len(buffer[: i + 1].strip()) >= MIN_CHUNK_CHARS:
                return i + 1
    return None
