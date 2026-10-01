from __future__ import annotations

from array import array
import sys

import numpy as np

from .buffer import AudioBuffer


PcmSamples = np.ndarray


def _decode_24bit_numpy(data: bytes) -> np.ndarray:
    """Decode little-endian signed 24-bit PCM into contiguous float32."""

    if not data:
        return np.empty(0, dtype=np.float32)

    raw = np.frombuffer(data, dtype=np.uint8)
    usable = (raw.size // 3) * 3
    if usable == 0:
        return np.empty(0, dtype=np.float32)

    triplets = raw[:usable].reshape(-1, 3)
    values = (
        triplets[:, 0].astype(np.int32)
        | (triplets[:, 1].astype(np.int32) << 8)
        | (triplets[:, 2].astype(np.int32) << 16)
    )

    # Sign-extend bit 23 without a Python loop.
    values = (values ^ 0x00800000) - 0x00800000
    return values.astype(np.float32) * np.float32(1.0 / 8388608.0)


def decode_pcm(buffer: AudioBuffer) -> PcmSamples:
    """Decode integer PCM into contiguous normalized float32 samples.

    The returned NumPy array is the canonical in-memory representation used by
    the mixer.  Decoding is vectorized so loading a large clip does not create
    one Python object per sample.
    """

    data = buffer.data
    width = int(buffer.bytes_per_sample)

    if not data:
        return np.empty(0, dtype=np.float32)

    if width == 1:
        values = np.frombuffer(data, dtype=np.uint8)
        result = values.astype(np.float32)
        result -= np.float32(128.0)
        result *= np.float32(1.0 / 128.0)
        return result

    if width == 2:
        values = np.frombuffer(data, dtype="<i2")
        result = values.astype(np.float32)
        result *= np.float32(1.0 / 32768.0)
        return result

    if width == 3:
        return _decode_24bit_numpy(data)

    if width == 4:
        values = np.frombuffer(data, dtype="<i4")
        result = values.astype(np.float32)
        result *= np.float32(1.0 / 2147483648.0)
        return result

    raise ValueError(f"Unsupported PCM sample width: {width}")


def encode_float32(samples: list[float] | array | np.ndarray) -> bytes:
    """Encode normalized samples as contiguous little-endian float32."""

    if len(samples) == 0:
        return b""

    if isinstance(samples, np.ndarray):
        if (
            samples.dtype == np.dtype("<f4")
            and samples.flags.c_contiguous
        ):
            return samples.tobytes(order="C")

        encoded = np.ascontiguousarray(samples, dtype="<f4")
        return encoded.tobytes(order="C")

    encoded = array("f", samples)

    if sys.byteorder != "little":
        encoded.byteswap()

    return encoded.tobytes()
