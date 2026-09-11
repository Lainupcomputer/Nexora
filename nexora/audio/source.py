from __future__ import annotations

from enum import Enum

from .bus import AudioBus
from .channel import AudioChannel
from .mixer import AudioMixer
from .sound import Sound
from .spatial import (
    calculate_distance,
    calculate_distance_attenuation,
    calculate_stereo_pan,
)


class AudioSourceState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class AudioSource:
    """Represents one playback instance of a Sound."""

    def __init__(
        self,
        sound: Sound,
        *,
        channel: AudioChannel = AudioChannel.SFX,
        volume: float = 1.0,
        loop: bool = False,
        position: tuple[float, float] = (0.0, 0.0),
        min_distance: float = 1.0,
        max_distance: float = 1000.0,
        pitch: float = 1.0,
        bus: AudioBus | None = None,
    ) -> None:
        self.sound = sound
        self.channel = channel

        self._volume = 1.0
        self._loop = bool(loop)
        self._state = AudioSourceState.STOPPED
        self._bus = bus

        # Playback position
        self._position = 0
        self._playback_position = 0.0

        # Spatial audio
        self._spatial_position = (0.0, 0.0)
        self._min_distance = 1.0
        self._max_distance = 1000.0

        # Playback pitch
        self._pitch = 1.0

        # Fade state
        self._fade_start_volume: float | None = None
        self._fade_target_volume: float | None = None
        self._fade_duration_frames = 0
        self._fade_elapsed_frames = 0
        self._fade_stop_on_complete = False

        self.volume = volume
        self.position_2d = position
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.pitch = pitch

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    @property
    def position(self) -> int:
        """Current playback position in frames."""

        return self._position

    @property
    def duration(self) -> float:
        """Total duration of the sound in seconds."""

        return self.sound.duration

    @property
    def position_seconds(self) -> float:
        """Current playback position in seconds."""

        frequency = self.sound.frequency

        if frequency <= 0:
            return 0.0

        return self._position / frequency

    @property
    def remaining(self) -> float:
        """Remaining playback time in seconds."""

        return max(
            0.0,
            self.duration - self.position_seconds,
        )

    @property
    def progress(self) -> float:
        """Playback progress from 0.0 to 1.0."""

        duration = self.duration

        if duration <= 0.0:
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                self.position_seconds / duration,
            ),
        )

    @property
    def state(self) -> AudioSourceState:
        return self._state

    @property
    def playing(self) -> bool:
        return self._state == AudioSourceState.PLAYING

    @property
    def paused(self) -> bool:
        return self._state == AudioSourceState.PAUSED

    @property
    def stopped(self) -> bool:
        return self._state == AudioSourceState.STOPPED

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                "Audio source volume must be between 0.0 and 1.0."
            )

        self._volume = value

    # ------------------------------------------------------------------
    # Bus
    # ------------------------------------------------------------------

    @property
    def bus(self) -> AudioBus | None:
        """Return the audio bus."""

        return self._bus

    @bus.setter
    def bus(
        self,
        value: AudioBus | None,
    ) -> None:
        """Set the audio bus."""

        self._bus = value

    # ------------------------------------------------------------------
    # Pitch
    # ------------------------------------------------------------------

    @property
    def pitch(self) -> float:
        """Return the playback pitch."""

        return self._pitch

    @pitch.setter
    def pitch(self, value: float) -> None:
        """Set the playback pitch."""

        value = float(value)

        if value <= 0.0:
            raise ValueError(
                "Audio source pitch must be greater than 0.0."
            )

        self._pitch = value

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    def loop(self, value: bool) -> None:
        self._loop = bool(value)

    # ------------------------------------------------------------------
    # Spatial audio
    # ------------------------------------------------------------------

    @property
    def position_2d(self) -> tuple[float, float]:
        """World-space position of the audio source."""

        return self._spatial_position

    @position_2d.setter
    def position_2d(
        self,
        value: tuple[float, float],
    ) -> None:
        if len(value) != 2:
            raise ValueError(
                "Audio source position must contain exactly two values."
            )

        self._spatial_position = (
            float(value[0]),
            float(value[1]),
        )

    @property
    def min_distance(self) -> float:
        """Distance at which the source has full volume."""

        return self._min_distance

    @min_distance.setter
    def min_distance(self, value: float) -> None:
        if value <= 0.0:
            raise ValueError(
                "Minimum audio distance must be greater than 0."
            )

        if value > self._max_distance:
            raise ValueError(
                "Minimum audio distance cannot exceed maximum distance."
            )

        self._min_distance = float(value)

    @property
    def max_distance(self) -> float:
        """Distance at which the source reaches zero volume."""

        return self._max_distance

    @max_distance.setter
    def max_distance(self, value: float) -> None:
        if value <= 0.0:
            raise ValueError(
                "Maximum audio distance must be greater than 0."
            )

        if value < self._min_distance:
            raise ValueError(
                "Maximum audio distance cannot be below minimum distance."
            )

        self._max_distance = float(value)

    # ------------------------------------------------------------------
    # Seeking
    # ------------------------------------------------------------------

    def seek(self, frame: int) -> None:
        """Seek to a specific frame."""

        if frame < 0:
            raise ValueError(
                "Audio position cannot be negative."
            )

        total_frames = self.sound.buffer.sample_count

        self._position = min(
            frame,
            total_frames,
        )

        self._playback_position = float(
            self._position
        )

    def seek_seconds(self, seconds: float) -> None:
        """Seek to a specific position in seconds."""

        if seconds < 0.0:
            raise ValueError(
                "Audio position cannot be negative."
            )

        frequency = self.sound.frequency

        if frequency <= 0:
            self._position = 0
            self._playback_position = 0.0
            return

        self.seek(
            int(seconds * frequency)
        )

    # ------------------------------------------------------------------
    # Fade
    # ------------------------------------------------------------------

    @property
    def fading(self) -> bool:
        """Return whether a fade is currently active."""

        return self._fade_duration_frames > 0

    def fade_in(self, duration: float) -> None:
        """Fade the source in from silence."""

        self._start_fade(
            start_volume=0.0,
            target_volume=self._volume,
            duration=duration,
            stop_on_complete=False,
        )

    def fade_out(self, duration: float) -> None:
        """Fade the source out to silence and stop."""

        self._start_fade(
            start_volume=self._volume,
            target_volume=0.0,
            duration=duration,
            stop_on_complete=True,
        )

    def _start_fade(
        self,
        *,
        start_volume: float,
        target_volume: float,
        duration: float,
        stop_on_complete: bool,
    ) -> None:
        """Start a volume fade."""

        if duration < 0.0:
            raise ValueError(
                "Fade duration cannot be negative."
            )

        if duration == 0.0:
            self._volume = target_volume
            self._clear_fade()

            if stop_on_complete:
                self._state = AudioSourceState.STOPPED
                self._position = 0
                self._playback_position = 0.0

            return

        duration_frames = max(
            1,
            int(duration * self.sound.frequency),
        )

        self._fade_start_volume = start_volume
        self._fade_target_volume = target_volume
        self._fade_duration_frames = duration_frames
        self._fade_elapsed_frames = 0
        self._fade_stop_on_complete = stop_on_complete

    def _get_fade_volume(self) -> float:
        """Return the current volume including the active fade."""

        if self._fade_duration_frames <= 0:
            return self._volume

        progress = (
            self._fade_elapsed_frames
            / self._fade_duration_frames
        )

        progress = max(
            0.0,
            min(1.0, progress),
        )

        start = self._fade_start_volume
        target = self._fade_target_volume

        if start is None or target is None:
            return self._volume

        return (
            start
            + (target - start) * progress
        )

    def _advance_fade(self, frame_count: int) -> None:
        """Advance the active fade by a number of frames."""

        if self._fade_duration_frames <= 0:
            return

        if frame_count <= 0:
            return

        self._fade_elapsed_frames += frame_count

        if (
            self._fade_elapsed_frames
            >= self._fade_duration_frames
        ):
            target = self._fade_target_volume

            if target is not None:
                self._volume = target

            stop_on_complete = (
                self._fade_stop_on_complete
            )

            self._clear_fade()

            if stop_on_complete:
                self._state = AudioSourceState.STOPPED
                self._position = 0
                self._playback_position = 0.0

    def _clear_fade(self) -> None:
        """Clear the current fade state."""

        self._fade_start_volume = None
        self._fade_target_volume = None
        self._fade_duration_frames = 0
        self._fade_elapsed_frames = 0
        self._fade_stop_on_complete = False

    # ------------------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------------------

    def play(self) -> None:
        """Start playback from the beginning."""

        self._position = 0
        self._playback_position = 0.0
        self._state = AudioSourceState.PLAYING

        self._clear_fade()

    def pause(self) -> None:
        """Pause playback."""

        if self._state == AudioSourceState.PLAYING:
            self._state = AudioSourceState.PAUSED

    def resume(self) -> None:
        """Resume paused playback."""

        if self._state == AudioSourceState.PAUSED:
            self._state = AudioSourceState.PLAYING

    def stop(self) -> None:
        """Stop playback and reset to the beginning."""

        self._state = AudioSourceState.STOPPED
        self._position = 0
        self._playback_position = 0.0

        self._clear_fade()

    # ------------------------------------------------------------------
    # Mixing
    # ------------------------------------------------------------------

    def get_effective_volume(
        self,
        mixer: AudioMixer,
    ) -> float:
        """Return the final volume after channel and bus mixing."""

        volume = (
            self._get_fade_volume()
            * mixer.get_effective_volume(self.channel)
        )

        # Master bus affects every audio source.
        volume *= mixer.master.effective_volume

        # Assigned bus affects only sources using that bus.
        if self._bus is not None:
            volume *= self._bus.effective_volume

        return volume

    def get_spatial_volume(
        self,
        listener_position: tuple[float, float],
    ) -> float:
        """Return the volume multiplier caused by distance."""

        distance = calculate_distance(
            self.position_2d,
            listener_position,
        )

        return calculate_distance_attenuation(
            distance=distance,
            min_distance=self.min_distance,
            max_distance=self.max_distance,
        )

    def get_spatial_parameters(
        self,
        listener_position: tuple[float, float],
    ) -> tuple[float, float]:
        """Return spatial volume and stereo pan."""

        volume = self.get_spatial_volume(
            listener_position,
        )

        pan = calculate_stereo_pan(
            self.position_2d,
            listener_position,
        )

        return volume, pan

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _finish(self) -> None:
        """Mark the source as naturally finished."""

        if self._fade_target_volume is not None:
            self._volume = self._fade_target_volume

        self._state = AudioSourceState.STOPPED
        self._clear_fade()
        
    def _advance_playback(
        self,
        amount: float,
    ) -> None:
        """Advance the internal playback position."""

        if amount < 0.0:
            raise ValueError(
                "Playback advance must not be negative."
            )

        self._playback_position += amount
        self._position = int(
            self._playback_position
        )