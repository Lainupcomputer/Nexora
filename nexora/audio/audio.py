from __future__ import annotations

from .bus import AudioBus
from .cache import AudioCache
from .channel import AudioChannel
from .device import AudioDevice
from .mixer import AudioMixer
from .player import AudioPlayer
from .sound import Sound


class AudioSystem:
    """
    Central audio system for the Nexora Engine.

    Technical output configuration is supplied during
    construction.

    Example:

        AudioSystem(
            frequency=48_000,
            channels=2,
            target_queue_frames=2048,
            max_update_frames=2048,
        )
    """

    def __init__(
        self,
        *,
        frequency: int = (
            AudioDevice.DEFAULT_FREQUENCY
        ),
        channels: int = (
            AudioDevice.DEFAULT_CHANNELS
        ),
        target_queue_frames: int = 2048,
        max_update_frames: int = 2048,
    ) -> None:
        # ======================================================
        # Validation
        # ======================================================

        frequency = int(
            frequency
        )

        channels = int(
            channels
        )

        target_queue_frames = int(
            target_queue_frames
        )

        max_update_frames = int(
            max_update_frames
        )

        if frequency <= 0:
            raise ValueError(
                "frequency must be greater than zero."
            )

        # ------------------------------------------------------
        # Nexora's current mixer is stereo.
        # ------------------------------------------------------

        if channels != 2:
            raise ValueError(
                "Nexora currently supports stereo "
                "audio output only."
            )

        if target_queue_frames <= 0:
            raise ValueError(
                "target_queue_frames must be greater than zero."
            )

        if max_update_frames <= 0:
            raise ValueError(
                "max_update_frames must be greater than zero."
            )

        # ======================================================
        # Mixer
        # ======================================================

        self.mixer = (
            AudioMixer()
        )

        self.mixer.add_bus(
            AudioBus(
                "Music"
            )
        )

        self.mixer.add_bus(
            AudioBus(
                "SFX"
            )
        )

        self.mixer.add_bus(
            AudioBus(
                "Ambient"
            )
        )

        self.mixer.add_bus(
            AudioBus(
                "Voice"
            )
        )

        # ======================================================
        # Cache
        # ======================================================

        self.cache = (
            AudioCache()
        )

        # ======================================================
        # Device
        # ======================================================

        self.device = (
            AudioDevice(
                frequency=frequency,
                channels=channels,
            )
        )

        # ======================================================
        # Player
        # ======================================================

        self.player = (
            AudioPlayer(
                self.device,
                self.mixer,
                target_queue_frames=(
                    target_queue_frames
                ),
                max_update_frames=(
                    max_update_frames
                ),
            )
        )

        # ======================================================
        # Music
        # ======================================================

        from .music import (
            MusicPlayer,
        )

        self.music = (
            MusicPlayer(
                self
            )
        )

        # ======================================================
        # Runtime
        # ======================================================

        self._initialized = False

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def initialized(
        self,
    ) -> bool:
        return (
            self._initialized
        )

    @property
    def frequency(
        self,
    ) -> int:
        return (
            self.device.frequency
        )

    @property
    def channels(
        self,
    ) -> int:
        return (
            self.device.channels
        )

    @property
    def target_queue_frames(
        self,
    ) -> int:
        return (
            self.player.target_queue_frames
        )

    @target_queue_frames.setter
    def target_queue_frames(
        self,
        value: int,
    ) -> None:
        self.player.target_queue_frames = (
            value
        )

    @property
    def max_update_frames(
        self,
    ) -> int:
        return (
            self.player.max_update_frames
        )

    @max_update_frames.setter
    def max_update_frames(
        self,
        value: int,
    ) -> None:
        self.player.max_update_frames = (
            value
        )

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        if self._initialized:
            return

        self.device.initialize()

        self._initialized = True

    def shutdown(
        self,
    ) -> None:
        if not self._initialized:
            return

        self.player.stop_all()

        self.device.shutdown()

        self._initialized = False

    # ==========================================================
    # CHANNEL VOLUME
    # ==========================================================

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
        return (
            self.mixer.get_volume(
                channel
            )
        )

    def get_effective_volume(
        self,
        channel: AudioChannel,
    ) -> float:
        return (
            self.mixer.get_effective_volume(
                channel
            )
        )

    # ==========================================================
    # CACHE
    # ==========================================================

    def load(
        self,
        path: str,
    ) -> Sound:
        """
        Load a sound through the audio cache.
        """

        return (
            self.cache.load(
                path
            )
        )

    def unload(
        self,
        path: str,
    ) -> None:
        """
        Remove a sound from the audio cache.
        """

        self.cache.remove(
            path
        )

    def clear_cache(
        self,
    ) -> None:
        """
        Clear all cached audio assets.
        """

        self.cache.clear()

    # ==========================================================
    # BUSES
    # ==========================================================

    def get_bus(
        self,
        name: str,
    ) -> AudioBus:
        """
        Return an audio bus by name.
        """

        return (
            self.mixer.get_bus(
                name
            )
        )

    def set_bus_volume(
        self,
        name: str,
        volume: float,
    ) -> None:
        """
        Set the volume of an audio bus.
        """

        self.mixer.get_bus(
            name
        ).volume = (
            volume
        )

    def get_bus_volume(
        self,
        name: str,
    ) -> float:
        """
        Return the volume of an audio bus.
        """

        return (
            self.mixer.get_bus(
                name
            ).volume
        )

    def set_bus_muted(
        self,
        name: str,
        muted: bool,
    ) -> None:
        """
        Set the mute state of an audio bus.
        """

        self.mixer.get_bus(
            name
        ).muted = (
            muted
        )

    def get_bus_muted(
        self,
        name: str,
    ) -> bool:
        """
        Return whether an audio bus is muted.
        """

        return bool(
            self.mixer.get_bus(
                name
            ).muted
        )

    # ==========================================================
    # RESET
    # ==========================================================

    def reset(
        self,
    ) -> None:
        """
        Reset mixer channels and buses to their defaults.
        """

        self.mixer.reset()