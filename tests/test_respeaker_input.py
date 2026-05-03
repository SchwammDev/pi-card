import io
import os

import pytest

from pi_card.adapters.respeaker_input import _drain_pipe_nonblocking


@pytest.fixture
def buffered_pipe():
    read_fd, write_fd = os.pipe()
    reader = io.BufferedReader(io.FileIO(read_fd, mode="r", closefd=False))
    yield reader, write_fd, read_fd
    reader.close()
    for fd in (read_fd, write_fd):
        try:
            os.close(fd)
        except OSError:
            pass


def _bytes_available(read_fd: int) -> int:
    import fcntl
    import struct
    import termios

    buf = bytearray(4)
    fcntl.ioctl(read_fd, termios.FIONREAD, buf)
    return struct.unpack("i", buf)[0]


def test_drain_clears_pending_bytes_from_the_kernel_pipe(buffered_pipe):
    reader, write_fd, read_fd = buffered_pipe
    os.write(write_fd, b"stale-audio-bytes")

    _drain_pipe_nonblocking(reader)

    assert _bytes_available(read_fd) == 0


def test_drain_returns_immediately_when_pipe_is_already_empty(buffered_pipe):
    reader, _, read_fd = buffered_pipe

    _drain_pipe_nonblocking(reader)

    assert _bytes_available(read_fd) == 0


def test_drain_leaves_subsequent_writes_readable(buffered_pipe):
    reader, write_fd, _ = buffered_pipe
    os.write(write_fd, b"old")
    _drain_pipe_nonblocking(reader)

    os.write(write_fd, b"fresh-bytes")

    assert reader.read(11) == b"fresh-bytes"


def test_drain_also_flushes_buffered_reader_cache(buffered_pipe):
    reader, write_fd, _ = buffered_pipe
    os.write(write_fd, b"prefetched-stale")
    reader.peek(1)

    _drain_pipe_nonblocking(reader)
    os.write(write_fd, b"fresh")

    assert reader.read(5) == b"fresh"
