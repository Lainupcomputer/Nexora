from __future__ import annotations

from .bus import AudioBus
from .channel import AudioChannel
from .device import AudioDevice
from .mixer import AudioMixer
from .player import AudioPlayer
from .cache import AudioCache
from .sound import Sound

class AudioSystem:
    """Central audio system for the Nexora Engine."""

    def __init__(self) -> None:
        self.mixer = AudioMixer()
        self.cache = AudioCache()
        self.device = AudioDevice()

        self.mixer.add_bus(
            AudioBus("Music")
        )

        self.mixer.add_bus(
            AudioBus("SFX")
        )

        self.mixer.add_bus(
            AudioBus("Ambient")
        )

        self.mixer.add_bus(
            AudioBus("Voice")
        )

        self.player = AudioPlayer(
            self.device,
            self.mixer,
        )

        from .music import MusicPlayer

        self.music = MusicPlayer(self)

        self._initialized = False

    @property
    def initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> None:
        if self._initialized:
            return

        self.device.initialize()
        self._initialized = True

    def shutdown(self) -> None:
        if not self._initialized:
            return

        self.player.stop_all()
        self.device.shutdown()
        self._initialized = False

    def set_volume(
        self,
        channel: AudioChannel,
        volume: float,
    ) -> None:
        self.mixer.set_volume(
            channel,
            volume,
        )

    def get_volume(
        self,
        channel: AudioChannel,
    ) -> float:
        return self.mixer.get_volume(channel)

    def load(
        self,
        path: str,
    ) -> Sound:
        """Load a sound through the audio cache."""

        return self.cache.load(path)

    def unload(
        self,
        path: str,
    ) -> None:
        """Remove a sound from the audio cache."""

        self.cache.remove(path)

    def clear_cache(self) -> None:
        """Clear all cached audio assets."""

        self.cache.clear()

    def get_effective_volume(
        self,
        channel: AudioChannel,
    ) -> float:
        return self.mixer.get_effective_volume(
            channel
        )

    def get_bus(
        self,
        name: str,
    ) -> AudioBus:
        """Return an audio bus by name."""

        return self.mixer.get_bus(name)

    def set_bus_volume(
        self,
        name: str,
        volume: float,
    ) -> None:
        """Set the volume of an audio bus."""

        self.mixer.get_bus(name).volume = volume

    def get_bus_volume(
        self,
        name: str,
    ) -> float:
        """Return the volume of an audio bus."""

        return self.mixer.get_bus(name).volume

    