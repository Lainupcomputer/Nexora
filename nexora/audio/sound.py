from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .buffer import AudioBuffer
from .pcm import PcmSamples, decode_pcm
from .wav import WavLoader


@dataclass(slots=True)
class Sound:
    """A decoded audio asset that can be played."""

    buffer: AudioBuffer
    path: Path | None = None

    _pcm_cache: PcmSamples | None = field(
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
    def pcm(self) -> PcmSamples:
        """Return decoded PCM samples, decoding only once.

        PCM is cached as one contiguous NumPy float32 array so the mixer can
        slice it without per-update conversion or Python sample objects.
        """

        if self._pcm_cache is None:
            pcm = decode_pcm(self.buffer)
            # Decoded assets are shared by all playback instances. Keep them
            # immutable so concurrent free-threaded mixers can safely read the
            # same cache without accidental in-place edits.
            pcm.setflags(write=False)
            self._pcm_cache = pcm

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
