from __future__ import annotations

import struct

from .buffer import AudioBuffer


def decode_pcm(buffer: AudioBuffer) -> list[float]:
    """Decode PCM audio data into normalized float samples."""

    data = buffer.data
    width = buffer.bytes_per_sample

    if width == 1:
        return [
            (sample - 128) / 128.0
            for sample in data
        ]

    if width == 2:
        count = len(data) // 2

        if not count:
            return []

        values = struct.unpack(
            f"<{count}h",
            data,
        )

        return [
            value / 32768.0
            for value in values
        ]

    if width == 3:
        samples: list[float] = []

        for index in range(0, len(data), 3):
            raw = int.from_bytes(
                data[index:index + 3],
                byteorder="little",
                signed=True,
            )

            samples.append(raw / 8388608.0)

        return samples

    if width == 4:
        count = len(data) // 4

        if not count:
            return []

        values = struct.unpack(
            f"<{count}i",
            data,
        )

        return [
            value / 2147483648.0
            for value in values
        ]

    raise ValueError(
        f"Unsupported PCM sample width: {width}"
    )


def encode_float32(samples: list[float]) -> bytes:
    """Encode normalized samples as little-endian float32."""

    if not samples:
        return b""

    return struct.pack(
        f"<{len(samples)}f",
        *samples,
    )