from __future__ import annotations

from .device import AudioDevice
from .listener import AudioListener
from .mixer import AudioMixer
from .pcm import encode_float32
from .source import (
    AudioSource,
    AudioSourceState,
)
from .spatial import calculate_pan_gains


class AudioPlayer:
    """
    Manages active audio sources and mixes them.

    Output format is defined by AudioDevice.

    Buffering behaviour is configured per AudioPlayer instance.

    Audio is generated on demand according to the amount already
    queued in SDL_AudioStream.

    This prevents the audio queue from growing with the game's
    frame rate.
    """

    def __init__(
        self,
        device: AudioDevice,
        mixer: AudioMixer,
        *,
        target_queue_frames: int = 2048,
        max_update_frames: int = 2048,
    ) -> None:
        self.device = device
        self.mixer = mixer

        # ======================================================
        # Buffer configuration
        # ======================================================

        target_queue_frames = int(
            target_queue_frames
        )

        max_update_frames = int(
            max_update_frames
        )

        if target_queue_frames <= 0:
            raise ValueError(
                "target_queue_frames must be greater than zero."
            )

        if max_update_frames <= 0:
            raise ValueError(
                "max_update_frames must be greater than zero."
            )

        self._target_queue_frames = (
            target_queue_frames
        )

        self._max_update_frames = (
            max_update_frames
        )

        # ======================================================
        # Listener
        # ======================================================

        self.listener = (
            AudioListener()
        )

        # ======================================================
        # Sources
        # ======================================================

        self._sources: list[
            AudioSource
        ] = []

    # ==========================================================
    # OUTPUT FORMAT
    # ==========================================================

    @property
    def output_channels(
        self,
    ) -> int:
        """
        Number of output channels.

        AudioDevice is the single source of truth.
        """

        return (
            self.device.channels
        )

    @property
    def output_frequency(
        self,
    ) -> int:
        """
        Output sample frequency.

        AudioDevice is the single source of truth.
        """

        return (
            self.device.frequency
        )

    # ==========================================================
    # BUFFER SETTINGS
    # ==========================================================

    @property
    def target_queue_frames(
        self,
    ) -> int:
        return (
            self._target_queue_frames
        )

    @target_queue_frames.setter
    def target_queue_frames(
        self,
        value: int,
    ) -> None:
        value = int(
            value
        )

        if value <= 0:
            raise ValueError(
                "target_queue_frames must be greater than zero."
            )

        self._target_queue_frames = (
            value
        )

    @property
    def max_update_frames(
        self,
    ) -> int:
        return (
            self._max_update_frames
        )

    @max_update_frames.setter
    def max_update_frames(
        self,
        value: int,
    ) -> None:
        value = int(
            value
        )

        if value <= 0:
            raise ValueError(
                "max_update_frames must be greater than zero."
            )

        self._max_update_frames = (
            value
        )

    # ==========================================================
    # SOURCES
    # ==========================================================

    @property
    def sources(
        self,
    ) -> tuple[
        AudioSource,
        ...
    ]:
        return tuple(
            self._sources
        )

    def add(
        self,
        source: AudioSource,
    ) -> None:
        if source not in self._sources:
            self._sources.append(
                source
            )

    def remove(
        self,
        source: AudioSource,
    ) -> None:
        if source in self._sources:
            self._sources.remove(
                source
            )

    # ==========================================================
    # PLAYBACK CONTROL
    # ==========================================================

    def play(
        self,
        source: AudioSource,
    ) -> None:
        if source not in self._sources:
            self.add(
                source
            )

        source.play()

    def pause(
        self,
        source: AudioSource,
    ) -> None:
        source.pause()

    def resume(
        self,
        source: AudioSource,
    ) -> None:
        source.resume()

    def stop(
        self,
        source: AudioSource,
    ) -> None:
        source.stop()

    def stop_all(
        self,
    ) -> None:
        for source in self._sources:
            source.stop()

    # ==========================================================
    # ACTIVE SOURCES
    # ==========================================================

    @property
    def has_playing_sources(
        self,
    ) -> bool:
        return any(
            source.state
            == AudioSourceState.PLAYING
            for source in self._sources
        )

    # ==========================================================
    # MIX
    # ==========================================================

    def mix(
        self,
        frame_count: int,
    ) -> bytes:
        """
        Mix active sources into float32 PCM.

        Nexora's current spatial mixer is stereo-based.

        AudioDevice.channels must therefore currently be 2.
        """

        frame_count = int(
            frame_count
        )

        if frame_count <= 0:
            return b""

        if self.output_channels != 2:
            raise RuntimeError(
                "Nexora AudioPlayer currently supports "
                "stereo output only."
            )

        mixed = [
            0.0
        ] * (
            frame_count
            * self.output_channels
        )

        for source in self._sources:
            if (
                source.state
                != AudioSourceState.PLAYING
            ):
                continue

            self._mix_source(
                source,
                mixed,
                frame_count,
            )

        self._clamp(
            mixed
        )

        return encode_float32(
            mixed
        )

    # ==========================================================
    # MIX SOURCE
    # ==========================================================

    def _mix_source(
        self,
        source: AudioSource,
        output: list[float],
        frame_count: int,
    ) -> None:
        samples = (
            source.sound.pcm
        )

        source_channels = (
            source.sound.channels
        )

        if source_channels <= 0:
            return

        total_frames = (
            len(
                samples
            )
            // source_channels
        )

        if total_frames <= 0:
            source.stop()
            return

        volume = (
            source.get_effective_volume(
                self.mixer
            )
        )

        (
            spatial_volume,
            pan,
        ) = (
            source.get_spatial_parameters(
                self.listener.position
            )
        )

        (
            left_gain,
            right_gain,
        ) = calculate_pan_gains(
            pan
        )

        volume *= (
            spatial_volume
        )

        output_index = 0

        for _ in range(
            frame_count
        ):
            if (
                source._playback_position
                >= total_frames
            ):
                if source.loop:
                    source._position = 0

                    source._playback_position = (
                        0.0
                    )

                else:
                    source._finish()
                    break

            position = (
                source._playback_position
            )

            base_position = int(
                position
            )

            fraction = (
                position
                - base_position
            )

            next_position = (
                base_position
                + 1
            )

            if (
                next_position
                >= total_frames
            ):
                next_position = (
                    base_position
                )

            # ==================================================
            # Mono source
            # ==================================================

            if source_channels == 1:
                current = (
                    samples[
                        base_position
                    ]
                )

                next_sample = (
                    samples[
                        next_position
                    ]
                )

                sample = (
                    current
                    + (
                        next_sample
                        - current
                    )
                    * fraction
                )

                left = (
                    sample
                )

                right = (
                    sample
                )

            # ==================================================
            # Stereo / multi-channel source
            #
            # Nexora currently uses the first two channels.
            # ==================================================

            else:
                current_index = (
                    base_position
                    * source_channels
                )

                next_index = (
                    next_position
                    * source_channels
                )

                current_left = (
                    samples[
                        current_index
                    ]
                )

                current_right = (
                    samples[
                        current_index
                        + 1
                    ]
                )

                next_left = (
                    samples[
                        next_index
                    ]
                )

                next_right = (
                    samples[
                        next_index
                        + 1
                    ]
                )

                left = (
                    current_left
                    + (
                        next_left
                        - current_left
                    )
                    * fraction
                )

                right = (
                    current_right
                    + (
                        next_right
                        - current_right
                    )
                    * fraction
                )

            # ==================================================
            # Output
            # ==================================================

            output[
                output_index
            ] += (
                left
                * volume
                * left_gain
            )

            output[
                output_index
                + 1
            ] += (
                right
                * volume
                * right_gain
            )

            output_index += (
                self.output_channels
            )

            # ==================================================
            # Playback position
            # ==================================================

            source._advance_playback(
                source.pitch
            )

            source._advance_fade(
                1
            )

            if (
                not source.loop
                and source._playback_position
                >= total_frames
            ):
                source._finish()

            if source.stopped:
                break

    # ==========================================================
    # CLAMP
    # ==========================================================

    @staticmethod
    def _clamp(
        samples: list[float],
    ) -> None:
        for (
            index,
            sample,
        ) in enumerate(
            samples
        ):
            if sample > 1.0:
                samples[
                    index
                ] = 1.0

            elif sample < -1.0:
                samples[
                    index
                ] = -1.0

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
    ) -> None:
        """
        Keep a small amount of PCM data queued for SDL.

        Audio generation depends on the current device queue,
        not on game frame rate.
        """

        if not self.device.initialized:
            raise RuntimeError(
                "Audio device is not initialized."
            )

        # ======================================================
        # Nothing playing
        # ======================================================

        if not self.has_playing_sources:
            return

        # ======================================================
        # Current queue depth
        # ======================================================

        queued_frames = (
            self.device.queued_frames()
        )

        if (
            queued_frames
            >= self.target_queue_frames
        ):
            return

        # ======================================================
        # Determine required frames
        # ======================================================

        missing_frames = (
            self.target_queue_frames
            - queued_frames
        )

        frame_count = min(
            missing_frames,
            self.max_update_frames,
        )

        if frame_count <= 0:
            return

        # ======================================================
        # Mix
        # ======================================================

        data = self.mix(
            frame_count
        )

        if not data:
            return

        # ======================================================
        # Queue
        # ======================================================

        self.device.write(
            data
        )