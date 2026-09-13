from __future__ import annotations


class AudioBus:
    """Controls shared volume and mute state for a group of audio."""

    def __init__(
        self,
        name: str,
        volume: float = 1.0,
        muted: bool = False,
    ) -> None:
        if not name:
            raise ValueError(
                "Audio bus name must not be empty."
            )

        self.name = name
        self._volume = 1.0
        self._muted = bool(muted)

        self.volume = volume

    @property
    def volume(self) -> float:
        """Return the bus volume."""

        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        """Set the bus volume."""

        value = float(value)

        if value < 0.0:
            raise ValueError(
                "Audio bus volume must not be negative."
            )

        self._volume = value

    @property
    def muted(self) -> bool:
        """Return whether the bus is muted."""

        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        """Set the mute state."""

        self._muted = bool(value)

    @property
    def effective_volume(self) -> float:
        """Return the volume currently applied to the bus."""

        if self._muted:
            return 0.0

        return self._volume

    def mute(self) -> None:
        """Mute the audio bus."""

        self._muted = True

    def unmute(self) -> None:
        """Unmute the audio bus."""

        self._muted = False

    def toggle_mute(self) -> None:
        """Toggle the mute state."""

        self._muted = not self._muted