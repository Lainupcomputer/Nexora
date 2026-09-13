from __future__ import annotations

from .device import AudioDevice
from .mixer import AudioMixer
from .pcm import encode_float32
from .source import AudioSource, AudioSourceState
from .listener import AudioListener
from .spatial import calculate_pan_gains


class AudioPlayer:
    """Manages active audio sources and mixes them."""

    OUTPUT_CHANNELS = 2
    OUTPUT_FREQUENCY = 48_000

    def __init__(
        self,
        device: AudioDevice,
        mixer: AudioMixer,
    ) -> None:
        self.device = device
        self.mixer = mixer
        self.listener = AudioListener()

        self._sources: list[AudioSource] = []

    @property
    def sources(self) -> tuple[AudioSource, ...]:
        return tuple(self._sources)

    def add(self, source: AudioSource) -> None:
        if source not in self._sources:
            self._sources.append(source)

    def remove(self, source: AudioSource) -> None:
        if source in self._sources:
            self._sources.remove(source)

    def play(self, source: AudioSource) -> None:
        if source not in self._sources:
            self.add(source)

        source.play()

    def pause(self, source: AudioSource) -> None:
        source.pause()

    def resume(self, source: AudioSource) -> None:
        source.resume()

    def stop(self, source: AudioSource) -> None:
        source.stop()

    def stop_all(self) -> None:
        for source in self._sources:
            source.stop()

    def mix(
        self,
        frame_count: int,
    ) -> bytes:
        """Mix active sources into stereo float32 PCM."""

        if frame_count <= 0:
            return b""

        mixed = [
            0.0
        ] * (
            frame_count
            * self.OUTPUT_CHANNELS
        )

        for source in self._sources:
            if source.state != AudioSourceState.PLAYING:
                continue

            self._mix_source(
                source,
                mixed,
                frame_count,
            )

        self._clamp(mixed)

        return encode_float32(mixed)

    def _mix_source(
        self,
        source: AudioSource,
        output: list[float],
        frame_count: int,
    ) -> None:
        samples = source.sound.pcm

        source_channels = source.sound.channels

        if source_channels <= 0:
            return

        total_frames = len(samples) // source_channels

        if total_frames <= 0:
            source.stop()
            return

        volume = source.get_effective_volume(
            self.mixer
        )

        spatial_volume, pan = source.get_spatial_parameters(
            self.listener.position
        )

        left_gain, right_gain = calculate_pan_gains(
            pan
        )

        volume *= spatial_volume

        output_index = 0

        for _ in range(frame_count):
            if source._playback_position >= total_frames:
                if source.loop:
                    source._position = 0
                    source._playback_position = 0.0
                else:
                    source._finish()
                    break

            position = source._playback_position

            base_position = int(position)
            fraction = position - base_position

            next_position = base_position + 1

            if next_position >= total_frames:
                next_position = base_position

            if source_channels == 1:
                current = samples[base_position]
                next_sample = samples[next_position]

                sample = (
                    current
                    + (next_sample - current)
                    * fraction
                )

                left = sample
                right = sample

            else:
                current_index = (
                    base_position
                    * source_channels
                )

                next_index = (
                    next_position
                    * source_channels
                )

                current_left = samples[current_index]
                current_right = samples[current_index + 1]

                next_left = samples[next_index]
                next_right = samples[next_index + 1]

                left = (
                    current_left
                    + (next_left - current_left)
                    * fraction
                )

                right = (
                    current_right
                    + (next_right - current_right)
                    * fraction
                )

            output[output_index] += (
                left
                * volume
                * left_gain
            )

            output[output_index + 1] += (
                right
                * volume
                * right_gain
            )

            output_index += 2

            source._advance_playback(
                source.pitch
            )

            source._advance_fade(1)

            if (
                not source.loop
                and source._playback_position >= total_frames
            ):
                source._finish()

            if source.stopped:
                break

    @staticmethod
    def _clamp(samples: list[float]) -> None:
        for index, sample in enumerate(samples):
            if sample > 1.0:
                samples[index] = 1.0

            elif sample < -1.0:
                samples[index] = -1.0

    def update(
        self,
        frame_count: int = 1024,
    ) -> None:
        """Mix and submit the next audio block."""

        if not self.device.initialized:
            raise RuntimeError(
                "Audio device is not initialized."
            )

        data = self.mix(frame_count)

        if data:
            self.device.write(data)