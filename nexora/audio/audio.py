from __future__ import annotations

from .bus import AudioBus
from .cache import AudioCache
from .device import AudioDevice
from .effects import AudioEffect
from .mixer import AudioMixer
from .player import AudioPlayer
from .preset import AudioPreset, AudioPresetRegistry
from .sound import Sound
from .stream import StreamedSound


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

        # ======================================================
        # DSP presets
        # ======================================================

        self.presets = AudioPresetRegistry(include_builtins=True)

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
    # CACHE
    # ==========================================================

    def load(
        self,
        path: str,
    ) -> Sound | StreamedSound:
        """
        Load a sound through the audio cache.
        """

        return (
            self.cache.load(
                path
            )
        )

    def load_stream(
        self,
        path: str,
    ) -> StreamedSound | Sound:
        """Load a WAV as metadata and stream decoded chunks during playback."""

        return self.cache.load_stream(path)

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

    def create_bus(
        self,
        name: str,
        *,
        parent: str | AudioBus | None = "Master",
        volume: float = 1.0,
        muted: bool = False,
        pan: float = 0.0,
        solo: bool = False,
        bus_id: str | None = None,
    ) -> AudioBus:
        """Create and register a dynamic audio bus."""
        return self.mixer.create_bus(
            name,
            parent=parent,
            volume=volume,
            muted=muted,
            pan=pan,
            solo=solo,
            bus_id=bus_id,
        )

    def has_bus(self, name: str) -> bool:
        return self.mixer.has_bus(name)

    def get_buses(self) -> tuple[AudioBus, ...]:
        return self.mixer.get_buses()

    def set_bus_parent(
        self,
        name: str,
        parent: str | AudioBus | None,
    ) -> None:
        self.mixer.set_bus_parent(name, parent)

    def remove_bus(
        self,
        name: str,
        *,
        reassign_to: str | AudioBus | None = "Master",
        reparent_children: bool = True,
    ) -> AudioBus:
        """Remove a bus and safely reassign sources using it."""
        removed = self.mixer.get_bus(name)

        if reassign_to is None:
            replacement: AudioBus | None = self.mixer.master
        elif isinstance(reassign_to, AudioBus):
            replacement = self.mixer.get_bus(reassign_to.name)
        else:
            replacement = self.mixer.get_bus(reassign_to)

        for source in self.player.sources:
            source_bus = source.bus
            if source_bus is removed or (
                isinstance(source_bus, str)
                and source_bus.casefold() in {removed.name.casefold(), removed.id.casefold()}
            ):
                source.bus = replacement

        child_target = replacement if reparent_children else removed.parent
        return self.mixer.remove_bus(
            name,
            reparent_children_to=child_target,
        )

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

    def add_bus_effect(
        self,
        name: str,
        effect: AudioEffect,
        *,
        index: int | None = None,
    ) -> AudioEffect:
        """Append/insert a DSP effect in a bus' ordered effect chain."""
        return self.mixer.get_bus(name).add_effect(effect, index=index)

    def remove_bus_effect(
        self,
        name: str,
        effect: AudioEffect,
    ) -> None:
        self.mixer.get_bus(name).remove_effect(effect)

    def clear_bus_effects(self, name: str) -> None:
        self.mixer.get_bus(name).clear_effects()

    def get_bus_effects(self, name: str) -> tuple[AudioEffect, ...]:
        return self.mixer.get_bus(name).effects

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

    def set_bus_pan(
        self,
        name: str,
        pan: float,
    ) -> None:
        """Set bus stereo balance from -1.0 (left) to +1.0 (right)."""
        self.mixer.get_bus(name).pan = pan

    def get_bus_pan(
        self,
        name: str,
    ) -> float:
        return self.mixer.get_bus(name).pan

    def set_bus_solo(
        self,
        name: str,
        solo: bool,
    ) -> None:
        """Enable or disable solo for a bus."""
        self.mixer.get_bus(name).solo = solo

    def get_bus_solo(
        self,
        name: str,
    ) -> bool:
        return bool(self.mixer.get_bus(name).solo)

    def get_bus_peak(
        self,
        name: str,
    ) -> tuple[float, float]:
        """Return the latest post-fader left/right peak meter values."""
        return self.mixer.get_bus(name).peak

    def get_bus_rms(
        self,
        name: str,
    ) -> tuple[float, float]:
        """Return the latest post-fader left/right RMS meter values."""
        return self.mixer.get_bus(name).rms

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

    def get_bus_by_id(self, bus_id: str) -> AudioBus:
        return self.mixer.get_bus_by_id(bus_id)

    def rename_bus(self, name_or_id: str, new_name: str) -> AudioBus:
        bus = self.mixer.get_bus(name_or_id)
        old_name = bus.name
        renamed = self.mixer.rename_bus(bus.id, new_name)
        # Keep legacy string-routed sources valid after a rename. Sources that
        # already store the AudioBus object need no changes because the id is stable.
        for source in self.player.sources:
            if isinstance(source.bus, str) and source.bus.casefold() == old_name.casefold():
                source.bus = renamed
        return renamed

    # ==========================================================
    # SEND / RETURN ROUTING
    # ==========================================================

    def add_send(
        self,
        source: str | AudioBus,
        target: str | AudioBus,
        *,
        amount: float = 1.0,
        pre_fader: bool = False,
        enabled: bool = True,
    ):
        return self.mixer.add_send(
            source, target, amount=amount, pre_fader=pre_fader, enabled=enabled
        )

    def remove_send(self, send_or_id) -> None:
        self.mixer.remove_send(send_or_id)

    def get_sends(self):
        return self.mixer.sends

    def set_send_amount(self, send_id: str, amount: float) -> None:
        self.mixer.set_send_amount(send_id, amount)

    def set_send_enabled(self, send_id: str, enabled: bool) -> None:
        self.mixer.set_send_enabled(send_id, enabled)

    def set_send_pre_fader(self, send_id: str, pre_fader: bool) -> None:
        self.mixer.set_send_pre_fader(send_id, pre_fader)

    # ==========================================================
    # DSP CONTROL
    # ==========================================================

    def set_bus_effects_bypassed(self, name: str, bypassed: bool) -> None:
        self.mixer.get_bus(name).effects_bypassed = bypassed

    def set_bus_effect_bypassed(self, name: str, index: int, bypassed: bool) -> None:
        self.mixer.get_bus(name).effects[int(index)].bypassed = bypassed

    def set_bus_effect_wet(self, name: str, index: int, wet: float) -> None:
        self.mixer.get_bus(name).effects[int(index)].wet = wet

    def set_bus_effect_parameter(
        self, name: str, index: int, parameter: str, value
    ) -> None:
        self.mixer.get_bus(name).effects[int(index)].set_parameter(parameter, value)

    def get_bus_effect_parameter(self, name: str, index: int, parameter: str):
        return self.mixer.get_bus(name).effects[int(index)].get_parameter(parameter)

    # ==========================================================
    # MASTER SAFETY / HEADROOM
    # ==========================================================

    def set_headroom_db(self, value: float) -> None:
        self.mixer.headroom_db = value

    def get_headroom_db(self) -> float:
        return self.mixer.headroom_db

    def enable_master_limiter(self, threshold: float = 0.98):
        return self.mixer.enable_master_limiter(threshold)

    def disable_master_limiter(self) -> None:
        self.mixer.disable_master_limiter()

    # ==========================================================
    # EXTENDED METERING
    # ==========================================================

    def get_bus_peak_dbfs(self, name: str) -> tuple[float, float]:
        return self.mixer.get_bus(name).peak_dbfs

    def get_bus_rms_dbfs(self, name: str) -> tuple[float, float]:
        return self.mixer.get_bus(name).rms_dbfs

    def get_bus_peak_hold(self, name: str) -> tuple[float, float]:
        return self.mixer.get_bus(name).peak_hold

    def get_bus_peak_hold_dbfs(self, name: str) -> tuple[float, float]:
        return self.mixer.get_bus(name).peak_hold_dbfs

    def get_bus_clipped(self, name: str) -> bool:
        return self.mixer.get_bus(name).clipped

    def clear_bus_peak_hold(self, name: str) -> None:
        self.mixer.get_bus(name).clear_peak_hold()

    # ==========================================================
    # DSP PRESETS
    # ==========================================================

    def register_audio_preset(
        self,
        name: str,
        effects,
        *,
        description: str = "",
        overwrite: bool = False,
    ) -> AudioPreset:
        return self.presets.register_effects(
            name,
            effects,
            description=description,
            overwrite=overwrite,
        )

    def capture_bus_preset(
        self,
        name: str,
        bus: str | AudioBus,
        *,
        description: str = "",
        overwrite: bool = False,
    ) -> AudioPreset:
        target = bus if isinstance(bus, AudioBus) else self.mixer.get_bus(bus)
        return self.presets.capture_bus(
            name,
            target,
            description=description,
            overwrite=overwrite,
        )

    def apply_audio_preset(
        self,
        preset: str,
        bus: str | AudioBus,
        *,
        replace: bool = True,
    ) -> tuple[AudioEffect, ...]:
        target = bus if isinstance(bus, AudioBus) else self.mixer.get_bus(bus)
        return self.presets.apply(preset, target, replace=replace)

    def get_audio_preset(self, name: str) -> AudioPreset:
        return self.presets.get(name)

    def get_audio_presets(self) -> tuple[AudioPreset, ...]:
        return self.presets.presets

    def remove_audio_preset(self, name: str) -> AudioPreset:
        return self.presets.unregister(name)

    def save_audio_preset(self, name: str, path) -> None:
        self.presets.save(name, path)

    def load_audio_preset(
        self,
        path,
        *,
        overwrite: bool = False,
        name: str | None = None,
    ) -> AudioPreset:
        return self.presets.load(path, overwrite=overwrite, name=name)

    # ==========================================================
    # MIXER SNAPSHOTS
    # ==========================================================

    def create_mixer_snapshot(self) -> dict:
        return self.mixer.create_snapshot()

    def restore_mixer_snapshot(
        self, snapshot: dict, *, restore_topology: bool = True
    ) -> None:
        self.mixer.restore_snapshot(snapshot, restore_topology=restore_topology)

    # ==========================================================
    # RESET
    # ==========================================================

    def reset(
        self,
    ) -> None:
        """
        Reset all registered audio buses to their defaults.
        """

        self.mixer.reset()
