from __future__ import annotations

from pathlib import Path

from .sound import Sound
from .wav import WavLoader


class AudioCache:
    """Caches loaded audio assets."""

    def __init__(self) -> None:
        self._sounds: dict[Path, Sound] = {}

    @property
    def sounds(self) -> tuple[Sound, ...]:
        """Return all cached sounds."""

        return tuple(self._sounds.values())


    @property
    def count(self) -> int:
        """Return the number of cached sounds."""

        return len(self._sounds)

    def contains(
        self,
        path: str | Path,
    ) -> bool:
        """Return whether a sound is cached."""

        path = self._normalize_path(path)

        return path in self._sounds

    @staticmethod
    def _normalize_path(
        path: str | Path,
    ) -> Path:
        """Normalize an audio asset path."""

        return Path(path).resolve()

    def load(
        self,
        path: str | Path,
    ) -> Sound:
        """Load and cache a sound."""

        path = self._normalize_path(path)

        if path in self._sounds:
            return self._sounds[path]

        sound = Sound.load(path)

        self._sounds[path] = sound

        return sound

    def get(
        self,
        path: str | Path,
    ) -> Sound | None:
        """Return a cached sound if available."""

        path = self._normalize_path(path)

        return self._sounds.get(path)

    def remove(
        self,
        path: str | Path,
    ) -> None:
        """Remove a sound from the cache."""

        path = self._normalize_path(path)

        if path not in self._sounds:
            return

        del self._sounds[path]

    def clear(self) -> None:
        """Clear all cached sounds."""

        self._sounds.clear()