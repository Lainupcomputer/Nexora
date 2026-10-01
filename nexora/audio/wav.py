from __future__ import annotations

import struct

import numpy as np
import wave
from pathlib import Path

from .buffer import AudioBuffer


class WavLoader:
    """Loads WAV files into AudioBuffer objects."""

    @staticmethod
    def _load_float_wav(path: Path) -> AudioBuffer:
        """Load a WAVE_FORMAT_IEEE_FLOAT file as signed 16-bit PCM."""

        raw_file = path.read_bytes()

        if (
            len(raw_file) < 12
            or raw_file[:4] != b"RIFF"
            or raw_file[8:12] != b"WAVE"
        ):
            raise ValueError(
                f"Invalid WAV header: {path}"
            )

        format_tag: int | None = None
        channels = 0
        frequency = 0
        bits_per_sample = 0
        audio_data_range: tuple[int, int] | None = None

        offset = 12

        while offset + 8 <= len(raw_file):
            chunk_id = raw_file[offset:offset + 4]
            chunk_size = struct.unpack_from(
                "<I",
                raw_file,
                offset + 4,
            )[0]
            chunk_start = offset + 8
            chunk_end = chunk_start + chunk_size

            if chunk_end > len(raw_file):
                raise ValueError(
                    f"Invalid WAV chunk: {path}"
                )

            if chunk_id == b"fmt ":
                if chunk_size < 16:
                    raise ValueError(
                        f"Invalid WAV format chunk: {path}"
                    )

                (
                    format_tag,
                    channels,
                    frequency,
                    _average_bytes_per_second,
                    _block_align,
                    bits_per_sample,
                ) = struct.unpack_from(
                    "<HHIIHH",
                    raw_file,
                    chunk_start,
                )

            elif chunk_id == b"data":
                # Keep offsets instead of slicing the complete data chunk.
                # A slice would duplicate a potentially very large WAV in
                # memory while the original file bytes are still retained.
                audio_data_range = (
                    chunk_start,
                    chunk_end,
                )

            offset = chunk_end + (chunk_size & 1)

        if format_tag != 3:
            raise ValueError(
                f"Unsupported WAV format: {format_tag!r}"
            )

        if channels <= 0:
            raise ValueError(
                f"Invalid channel count in WAV file: {path}"
            )

        if frequency <= 0:
            raise ValueError(
                f"Invalid sample rate in WAV file: {path}"
            )

        if bits_per_sample != 32:
            raise ValueError(
                "Only 32-bit float WAV files are supported: "
                f"{path}"
            )

        if audio_data_range is None:
            raise ValueError(
                f"Invalid float WAV data: {path}"
            )

        data_start, data_end = audio_data_range
        data_size = data_end - data_start

        if data_size % 4:
            raise ValueError(
                f"Invalid float WAV data: {path}"
            )

        # Convert the complete float WAV payload in native NumPy loops.
        # This avoids a Python iteration and one Python float allocation per
        # sample when loading long 32-bit-float recordings.
        samples = np.frombuffer(
            memoryview(raw_file)[data_start:data_end],
            dtype="<f4",
        ).astype(np.float32, copy=True)
        np.nan_to_num(samples, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        np.clip(samples, -1.0, 1.0, out=samples)

        positive = samples >= 0.0
        scaled = samples * np.float32(32768.0)
        scaled[positive] = samples[positive] * np.float32(32767.0)
        pcm_data = scaled.astype("<i2").tobytes(order="C")

        return AudioBuffer(
            data=pcm_data,
            frequency=frequency,
            channels=channels,
            bytes_per_sample=2,
        )

    def load(self, path: str | Path) -> AudioBuffer:
        path = Path(path)

        if not path.is_file():
            raise FileNotFoundError(
                f"WAV file not found: {path}"
            )

        try:
            with wave.open(str(path), "rb") as wav:
                channels = wav.getnchannels()
                frequency = wav.getframerate()
                sample_width = wav.getsampwidth()
                frame_count = wav.getnframes()

                data = wav.readframes(frame_count)

        except wave.Error as exc:
            try:
                return self._load_float_wav(path)
            except (ValueError, struct.error) as float_exc:
                raise ValueError(
                    f"Failed to load WAV file: {path}"
                ) from float_exc

        if channels <= 0:
            raise ValueError(
                f"Invalid channel count in WAV file: {path}"
            )

        if frequency <= 0:
            raise ValueError(
                f"Invalid sample rate in WAV file: {path}"
            )

        if sample_width <= 0:
            raise ValueError(
                f"Invalid sample width in WAV file: {path}"
            )

        return AudioBuffer(
            data=data,
            frequency=frequency,
            channels=channels,
            bytes_per_sample=sample_width,
        )
