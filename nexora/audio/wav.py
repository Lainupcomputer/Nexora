from __future__ import annotations

import wave
from pathlib import Path

from .buffer import AudioBuffer


class WavLoader:
    """Loads WAV files into AudioBuffer objects."""

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
            raise ValueError(
                f"Failed to load WAV file: {path}"
            ) from exc

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