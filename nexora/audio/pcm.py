from __future__ import annotations

from array import array
from collections.abc import Iterable
import struct
import sys

from .buffer import AudioBuffer


PcmSamples = list[float] | array

# Python lists store one pointer plus a separate Python float object for every
# sample.  That becomes extremely expensive for music tracks.  Keep small
# clips as lists for backwards compatibility, but use a packed float array for
# anything larger than a short audio event.
_COMPACT_SAMPLE_THRESHOLD = 4096


def _compact(values: Iterable[float]) -> array:
    return array("f", values)


def _decode_24bit_samples(data: bytes) -> Iterable[float]:
    for index in range(0, len(data), 3):
        raw = int.from_bytes(
            data[index:index + 3],
            byteorder="little",
            signed=True,
        )
        yield raw / 8388608.0


def decode_pcm(buffer: AudioBuffer) -> PcmSamples:
    """Decode PCM audio into normalized samples without a large object spike."""

    data = buffer.data
    width = buffer.bytes_per_sample

    if width == 1:
        if len(data) > _COMPACT_SAMPLE_THRESHOLD:
            return _compact(
                (sample - 128) / 128.0
                for sample in data
            )

        return [
            (sample - 128) / 128.0
            for sample in data
        ]

    if width == 2:
        count = len(data) // 2

        if not count:
            return []

        if count > _COMPACT_SAMPLE_THRESHOLD:
            return _compact(
                value / 32768.0
                for (value,) in struct.iter_unpack(
                    "<h",
                    data,
                )
            )

        values = struct.unpack(
            f"<{count}h",
            data,
        )

        return [
            value / 32768.0
            for value in values
        ]

    if width == 3:
        if len(data) // 3 > _COMPACT_SAMPLE_THRESHOLD:
            return _compact(
                _decode_24bit_samples(data)
            )

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

        if count > _COMPACT_SAMPLE_THRESHOLD:
            return _compact(
                value / 2147483648.0
                for (value,) in struct.iter_unpack(
                    "<i",
                    data,
                )
            )

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
    """Encode normalized samples as little-endian float32.

    Using a packed array avoids the large temporary argument tuple created by
    ``struct.pack(*samples)`` on every audio update.
    """

    if not samples:
        return b""

    encoded = array("f", samples)

    if sys.byteorder != "little":
        encoded.byteswap()

    return encoded.tobytes()
