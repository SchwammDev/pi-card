import os

import pytest

from pi_card.adapters.respeaker_input import _drain_pipe_nonblocking


@pytest.fixture
def pipe():
    read_fd, write_fd = os.pipe()
    yield read_fd, write_fd
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


def test_drain_clears_pending_bytes_from_the_pipe(pipe):
    read_fd, write_fd = pipe
    os.write(write_fd, b"stale-audio-bytes")

    _drain_pipe_nonblocking(read_fd)

    assert _bytes_available(read_fd) == 0


def test_drain_returns_immediately_when_pipe_is_already_empty(pipe):
    read_fd, _ = pipe

    _drain_pipe_nonblocking(read_fd)

    assert _bytes_available(read_fd) == 0


def test_drain_leaves_subsequent_writes_readable(pipe):
    read_fd, write_fd = pipe
    os.write(write_fd, b"old")
    _drain_pipe_nonblocking(read_fd)

    os.write(write_fd, b"fresh")

    assert os.read(read_fd, 5) == b"fresh"
