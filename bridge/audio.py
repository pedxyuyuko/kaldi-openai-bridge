"""AudioBuffer – accumulate raw PCM bytes and export a valid WAV file."""

from __future__ import annotations

import struct
from typing import Final

# struct.pack format for a 44-byte RIFF/WAVE header (little-endian).
#   <4s I 4s 4s I H H I I H H 4s I
#   RIFF  size  WAVE  fmt   ...    data  chunk_size
_WAV_HEADER_FMT: Final[str] = "<4sI4s4sIHHIIHH4sI"

# Bytes per second for the default format: 16000 Hz * 2 bytes * 1 channel
_DEFAULT_BYTES_PER_SEC: Final[int] = 32000


class AudioBuffer:
    """Accumulates raw PCM bytes and can export them as a WAV file.

    Default format: 16 kHz, 16-bit signed little-endian (S16LE), mono.
    """

    def __init__(
        self,
        sample_rate: int = 16_000,
        sample_width: int = 2,
        channels: int = 1,
    ) -> None:
        self._sample_rate: int = sample_rate
        self._sample_width: int = sample_width  # bytes per sample
        self._channels: int = channels
        self._buf: bytearray = bytearray()

    # ── public API ────────────────────────────────────────────────────

    def feed(self, data: bytes) -> None:
        """Append raw PCM *data* to the internal buffer."""
        self._buf.extend(data)

    def to_wav(self) -> bytes:
        """Return a complete WAV file (header + PCM data) as ``bytes``."""
        data_size = len(self._buf)
        header = self._build_header(data_size)
        return header + bytes(self._buf)

    def duration_s(self) -> float:
        """Return the current audio duration in seconds."""
        bytes_per_sec = self._sample_rate * self._sample_width * self._channels
        if bytes_per_sec == 0:
            return 0.0
        return len(self._buf) / bytes_per_sec

    def clear(self) -> None:
        """Reset the buffer."""
        self._buf.clear()

    def size_bytes(self) -> int:
        """Return the size of the accumulated PCM data in bytes."""
        return len(self._buf)

    # ── internal helpers ──────────────────────────────────────────────

    def _build_header(self, data_size: int) -> bytes:
        """Construct a 44-byte RIFF/WAV header."""
        byte_rate = self._sample_rate * self._sample_width * self._channels
        block_align = self._channels * self._sample_width
        return struct.pack(
            _WAV_HEADER_FMT,
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,  # PCM format chunk size
            1,  # audio format: PCM
            self._channels,
            self._sample_rate,
            byte_rate,
            block_align,
            self._sample_width * 8,  # bits per sample
            b"data",
            data_size,
        )
