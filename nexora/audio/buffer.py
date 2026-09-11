from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AudioBuffer:
    """Decoded PCM audio data."""

    data: bytes
    frequency: int
    channels: int
    bytes_per_sample: int

    @property
    def sample_count(self) -> int:
        frame_size = (
            self.channels * self.bytes_per_sample
        )

        if frame_size == 0:
            return 0

        return len(self.data) // frame_size

    @property
    def duration(self) -> float:
        if self.frequency <= 0:
            return 0.0

        return self.sample_count / self.frequency

    @property
    def size(self) -> int:
        return len(self.data)

    def is_empty(self) -> bool:
        return not self.data