from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .buffer import AudioBuffer
from .pcm import decode_pcm
from .wav import WavLoader


@dataclass(slots=True)
class Sound:
    """A decoded audio asset that can be played."""

    buffer: AudioBuffer
    path: Path | None = None

    _pcm_cache: list[float] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    @property
    def duration(self) -> float:
        return self.buffer.duration

    @property
    def frequency(self) -> int:
        return self.buffer.frequency

    @property
    def channels(self) -> int:
        return self.buffer.channels

    @property
    def size(self) -> int:
        return self.buffer.size

    @property
    def pcm(self) -> list[float]:
        """Return decoded PCM samples, decoding only once."""

        if self._pcm_cache is None:
            self._pcm_cache = decode_pcm(
                self.buffer
            )

        return self._pcm_cache

    def clear_pcm_cache(self) -> None:
        """Clear the decoded PCM cache."""

        self._pcm_cache = None

    @classmethod
    def load(cls, path: str | Path) -> Sound:
        path = Path(path).resolve()

        buffer = WavLoader().load(path)

        return cls(
            buffer=buffer,
            path=path,
        )