from __future__ import annotations

from .bus import AudioBus
from .channel import AudioChannel


class AudioMixer:
    """Controls Nexora's audio channel volumes and audio buses."""

    def __init__(self) -> None:
        self._volumes: dict[AudioChannel, float] = {
            AudioChannel.MASTER: 1.0,
            AudioChannel.MUSIC: 1.0,
            AudioChannel.SFX: 1.0,
            AudioChannel.AMBIENT: 1.0,
            AudioChannel.VOICE: 1.0,
        }

        self._buses: dict[str, AudioBus] = {}

        self.add_bus(
            AudioBus("Master")
        )

    @property
    def buses(self) -> tuple[AudioBus, ...]:
        """Return all registered audio buses."""

        return tuple(self._buses.values())

    @property
    def master(self) -> AudioBus:
        """Return the master audio bus."""

        return self._buses["Master"]

    def add_bus(
        self,
        bus: AudioBus,
    ) -> None:
        """Register an audio bus."""

        if bus.name in self._buses:
            raise ValueError(
                f"Audio bus already exists: {bus.name}"
            )

        self._buses[bus.name] = bus

    def remove_bus(
        self,
        name: str,
    ) -> None:
        """Remove an audio bus."""

        if name == "Master":
            raise ValueError(
                "The master audio bus cannot be removed."
            )

        if name not in self._buses:
            raise KeyError(
                f"Unknown audio bus: {name}"
            )

        del self._buses[name]

    def get_bus(
        self,
        name: str,
    ) -> AudioBus:
        """Return an audio bus by name."""

        try:
            return self._buses[name]
        except KeyError:
            raise KeyError(
                f"Unknown audio bus: {name}"
            ) from None

    def set_volume(
        self,
        channel: AudioChannel,
        volume: float,
    ) -> None:
        """Set the volume of an audio channel."""

        if not 0.0 <= volume <= 1.0:
            raise ValueError(
                "Audio volume must be between 0.0 and 1.0."
            )

        self._volumes[channel] = volume

    def get_volume(
        self,
        channel: AudioChannel,
    ) -> float:
        """Return the volume of an audio channel."""

        return self._volumes[channel]

    def get_effective_volume(
        self,
        channel: AudioChannel,
    ) -> float:
        """Return the effective volume of an audio channel."""

        if channel == AudioChannel.MASTER:
            return self._volumes[
                AudioChannel.MASTER
            ]

        return (
            self._volumes[AudioChannel.MASTER]
            * self._volumes[channel]
        )

    def reset(self) -> None:
        """Reset all audio channel volumes."""

        for channel in self._volumes:
            self._volumes[channel] = 1.0

        for bus in self._buses.values():
            bus.volume = 1.0
            bus.muted = False