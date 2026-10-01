from __future__ import annotations

from threading import RLock

import numpy as np

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
        self._sources_lock = RLock()

        # Reuse the hot output buffer instead of allocating a new ndarray on
        # every game update. ``mix()`` owns this buffer while the source lock
        # is held, which also makes this safe when Nexora runs free-threaded.
        self._mix_buffer = np.zeros(
            self._max_update_frames * self.output_channels,
            dtype=np.float32,
        )

        # Per-bus work buffers make real hierarchical DSP possible. Sources
        # are mixed into their assigned bus first; buses are then processed
        # deepest-first and routed into their parent. Buffers are retained and
        # reused to avoid allocations in the real-time path.
        self._bus_buffers: dict[str, np.ndarray] = {}
        self._send_buffer = np.zeros_like(self._mix_buffer)

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
        with self._sources_lock:
            return tuple(
                self._sources
            )

    def add(
        self,
        source: AudioSource,
    ) -> None:
        with self._sources_lock:
            if source not in self._sources:
                self._sources.append(
                    source
                )

    def remove(
        self,
        source: AudioSource,
    ) -> None:
        with self._sources_lock:
            if source in self._sources:
                self._sources.remove(
                    source
                )

            source._close_stream_reader()

    # ==========================================================
    # PLAYBACK CONTROL
    # ==========================================================

    def play(
        self,
        source: AudioSource,
    ) -> None:
        with self._sources_lock:
            if source not in self._sources:
                self._sources.append(source)
            source.play()

    def pause(
        self,
        source: AudioSource,
    ) -> None:
        with self._sources_lock:
            source.pause()

    def resume(
        self,
        source: AudioSource,
    ) -> None:
        with self._sources_lock:
            source.resume()

    def stop(
        self,
        source: AudioSource,
    ) -> None:
        with self._sources_lock:
            source.stop()

    def stop_all(
        self,
    ) -> None:
        with self._sources_lock:
            for source in self._sources:
                source.stop()
            self._prune_stopped_sources_locked()

    def _prune_stopped_sources_locked(self) -> int:
        """Drop stopped sources while ``_sources_lock`` is already held.

        Audio sources are short-lived runtime objects. Keeping naturally
        finished or explicitly stopped sources in the player retains their
        Sound/StreamedSound references and, for streams, can also retain a
        decoded NumPy window. This helper makes source ownership bounded.
        Paused sources are intentionally kept.
        """

        if not self._sources:
            return 0

        survivors: list[AudioSource] = []
        removed = 0
        for source in self._sources:
            if source.state == AudioSourceState.STOPPED:
                source._close_stream_reader()
                removed += 1
            else:
                survivors.append(source)

        if removed:
            self._sources[:] = survivors

        return removed

    def prune_stopped_sources(self) -> int:
        """Remove finished/stopped sources and return the number removed."""

        with self._sources_lock:
            return self._prune_stopped_sources_locked()

    # ==========================================================
    # ACTIVE SOURCES
    # ==========================================================

    @property
    def has_playing_sources(
        self,
    ) -> bool:
        with self._sources_lock:
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

        sample_count = frame_count * self.output_channels
        if sample_count > self._mix_buffer.size:
            # Grow geometrically so an occasional larger request does not
            # cause repeated reallocations on subsequent updates.
            new_size = max(sample_count, self._mix_buffer.size * 2)
            self._mix_buffer = np.zeros(new_size, dtype=np.float32)

        mixed = self._mix_buffer[:sample_count]
        mixed.fill(0.0)

        # Source state and the shared work buffers are owned for the duration
        # of one mix. Sources first write into their assigned bus. The bus
        # graph is processed afterwards so DSP order is deterministic:
        # source -> bus effects -> bus gain -> parent -> ... -> master.
        with self._sources_lock:
            bus_buffers = self._prepare_bus_buffers(sample_count)

            for source in self._sources:
                if source.state != AudioSourceState.PLAYING:
                    continue

                bus = self.mixer.resolve_bus(source.bus)
                self._mix_source(
                    source,
                    bus_buffers[bus.id][:sample_count],
                    frame_count,
                )

            self._process_bus_graph(
                bus_buffers,
                mixed,
                frame_count,
                sample_count,
            )

            # Sources can finish naturally during the block above. Release
            # them immediately instead of waiting for another update tick.
            self._prune_stopped_sources_locked()

        self._clamp(mixed)
        return encode_float32(mixed)

    def _prepare_bus_buffers(
        self,
        sample_count: int,
    ) -> dict[str, np.ndarray]:
        """Return zeroed reusable work buffers keyed by stable bus id."""

        active_keys: set[str] = set()
        for bus in self.mixer.buses:
            key = bus.id
            active_keys.add(key)
            buffer = self._bus_buffers.get(key)
            if buffer is None or buffer.size < sample_count:
                old_size = 0 if buffer is None else buffer.size
                new_size = max(sample_count, old_size * 2, self._mix_buffer.size)
                buffer = np.zeros(new_size, dtype=np.float32)
                self._bus_buffers[key] = buffer
            buffer[:sample_count].fill(0.0)

        for key in tuple(self._bus_buffers):
            if key not in active_keys:
                del self._bus_buffers[key]

        if self._send_buffer.size < sample_count:
            new_size = max(sample_count, self._send_buffer.size * 2, self._mix_buffer.size)
            self._send_buffer = np.zeros(new_size, dtype=np.float32)

        return self._bus_buffers

    def _route_send(
        self,
        block: np.ndarray,
        target: np.ndarray,
        amount: float,
        sample_count: int,
    ) -> None:
        if amount <= 0.0:
            return
        if amount == 1.0:
            np.add(target, block, out=target)
            return
        scratch = self._send_buffer[:sample_count]
        np.multiply(block, amount, out=scratch)
        np.add(target, scratch, out=target)

    def _process_bus_graph(
        self,
        bus_buffers: dict[str, np.ndarray],
        output: np.ndarray,
        frame_count: int,
        sample_count: int,
    ) -> None:
        """Process the acyclic routing graph including pre/post-fader sends."""

        for bus in self.mixer.processing_order():
            block = bus_buffers[bus.id][:sample_count]
            frames = block.reshape(frame_count, self.output_channels)

            if bus.muted or not self.mixer.is_bus_audible(bus):
                block.fill(0.0)
                bus.reset_meter(clear_hold=False)
            else:
                # Headroom is a Master pre-DSP stage so the complete master
                # chain, including a limiter, sees the reserved level.
                if bus is self.mixer.master:
                    headroom = self.mixer.headroom_gain
                    if headroom != 1.0:
                        np.multiply(block, headroom, out=block)

                bus.process_effects(
                    frames,
                    sample_rate=self.output_frequency,
                    channels=self.output_channels,
                )

                # Pre-fader sends branch after bus DSP but before fader/pan.
                for send in self.mixer.get_sends_from(bus):
                    if not send.enabled or not send.pre_fader:
                        continue
                    target = bus_buffers[send.target_bus_id][:sample_count]
                    self._route_send(block, target, send.amount, sample_count)

                if bus.volume != 1.0:
                    np.multiply(block, bus.volume, out=block)

                if bus.pan != 0.0:
                    left_gain, right_gain = calculate_pan_gains(bus.pan)
                    np.multiply(frames[:, 0], left_gain, out=frames[:, 0])
                    np.multiply(frames[:, 1], right_gain, out=frames[:, 1])

                # Optional dedicated safety limiter is always the final Master
                # DSP stage, after the Master fader/pan and before metering.
                if bus is self.mixer.master:
                    limiter = self.mixer.master_limiter
                    if limiter is not None and limiter.enabled:
                        limiter_scratch = self._send_buffer[:sample_count].reshape(
                            frame_count, self.output_channels
                        )
                        limiter.process_mixed(
                            frames,
                            limiter_scratch,
                            sample_rate=self.output_frequency,
                            channels=self.output_channels,
                        )

                bus.update_meter(frames)

                # Post-fader sends receive exactly what this bus contributes to
                # its regular parent route.
                for send in self.mixer.get_sends_from(bus):
                    if not send.enabled or send.pre_fader:
                        continue
                    target = bus_buffers[send.target_bus_id][:sample_count]
                    self._route_send(block, target, send.amount, sample_count)

            if bus is self.mixer.master:
                np.copyto(output, block)
            else:
                parent_bus = bus.parent or self.mixer.master
                parent = bus_buffers[parent_bus.id][:sample_count]
                np.add(parent, block, out=parent)

    # ==========================================================
    # MIX SOURCE
    # ==========================================================

    def _mix_source(
        self,
        source: AudioSource,
        output: np.ndarray,
        frame_count: int,
    ) -> None:
        if getattr(source.sound, "streaming", False):
            self._mix_stream_source(
                source,
                output,
                frame_count,
            )
            return

        # Most game audio runs at pitch 1.0 without an active fade. Avoid the
        # per-sample interpolation and AudioSource method calls in that hot
        # path. Heartbeat, voices and short SFX use this path and it is much
        # cheaper when several sources are active at once.
        if (
            source.pitch == 1.0
            and not source.fading
            and source._playback_position
            == int(source._playback_position)
        ):
            self._mix_source_fast(
                source,
                output,
                frame_count,
            )
            return

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
            source.get_source_volume()
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

    def _mix_source_fast(
        self,
        source: AudioSource,
        output: np.ndarray,
        frame_count: int,
    ) -> None:
        """Mix an unpitched, non-fading PCM source without interpolation."""

        samples = source.sound.pcm
        source_channels = int(source.sound.channels)

        if source_channels <= 0:
            return

        total_frames = len(samples) // source_channels
        frames = samples[: total_frames * source_channels].reshape(
            total_frames,
            source_channels,
        )

        if total_frames <= 0:
            source.stop()
            return

        volume = source.get_source_volume()
        spatial_volume, pan = source.get_spatial_parameters(
            self.listener.position,
        )
        left_gain, right_gain = calculate_pan_gains(pan)
        left_scale = volume * spatial_volume * left_gain
        right_scale = volume * spatial_volume * right_gain

        frame = int(source._playback_position)
        remaining = int(frame_count)
        output_index = 0

        while remaining > 0:
            if frame >= total_frames:
                if source.loop:
                    frame = 0
                    source._playback_position = 0.0
                    source._position = 0
                else:
                    source._finish()
                    break

            count = min(
                remaining,
                total_frames - frame,
            )

            out = output[output_index:output_index + count * 2].reshape(-1, 2)

            chunk = frames[frame:frame + count]
            if source_channels == 1:
                mono = chunk[:, 0]
                out[:, 0] += mono * left_scale
                out[:, 1] += mono * right_scale
            else:
                out[:, 0] += chunk[:, 0] * left_scale
                out[:, 1] += chunk[:, 1] * right_scale

            output_index += count * 2

            frame += count
            remaining -= count
            source._playback_position = float(frame)
            source._position = frame

            if not source.loop and frame >= total_frames:
                source._finish()
                break

    def _mix_stream_source(
        self,
        source: AudioSource,
        output: np.ndarray,
        frame_count: int,
    ) -> None:
        """Mix a bounded WAV window without creating a full PCM cache."""

        source_channels = int(source.sound.channels)
        total_frames = int(source.sound.sample_count)

        if source_channels <= 0 or total_frames <= 0:
            source.stop()
            return

        if (
            source.pitch == 1.0
            and not source.fading
            and source._playback_position
            == int(source._playback_position)
        ):
            self._mix_stream_source_fast(
                source,
                output,
                frame_count,
            )
            return

        volume = source.get_source_volume()
        spatial_volume, pan = source.get_spatial_parameters(
            self.listener.position,
        )
        left_gain, right_gain = calculate_pan_gains(pan)
        volume *= spatial_volume

        output_index = 0

        for _ in range(frame_count):
            if source._playback_position >= total_frames:
                if source.loop:
                    source.seek(0)
                else:
                    source._finish()
                    break

            position = source._playback_position
            base_position = int(position)
            fraction = position - base_position
            next_position = base_position + 1

            if next_position >= total_frames:
                next_position = 0 if source.loop else base_position

            if source_channels == 1:
                current = source._stream_sample(base_position, 0)
                next_sample = source._stream_sample(next_position, 0)
                sample = current + (next_sample - current) * fraction
                left = sample
                right = sample
            else:
                current_left = source._stream_sample(base_position, 0)
                current_right = source._stream_sample(base_position, 1)
                next_left = source._stream_sample(next_position, 0)
                next_right = source._stream_sample(next_position, 1)
                left = current_left + (next_left - current_left) * fraction
                right = current_right + (next_right - current_right) * fraction

            output[output_index] += left * volume * left_gain
            output[output_index + 1] += right * volume * right_gain
            output_index += self.output_channels

            source._advance_playback(source.pitch)
            source._advance_fade(1)

            if (
                not source.loop
                and source._playback_position >= total_frames
            ):
                source._finish()
                break

    def _mix_stream_source_fast(
        self,
        source: AudioSource,
        output: np.ndarray,
        frame_count: int,
    ) -> None:
        """Mix sequential streamed PCM with one bounded chunk lookup."""

        source_channels = int(source.sound.channels)
        total_frames = int(source.sound.sample_count)
        reader = source._ensure_stream_reader()

        if (
            source_channels <= 0
            or total_frames <= 0
            or reader is None
        ):
            source.stop()
            return

        volume = source.get_source_volume()
        spatial_volume, pan = source.get_spatial_parameters(
            self.listener.position,
        )
        left_gain, right_gain = calculate_pan_gains(pan)
        left_scale = volume * spatial_volume * left_gain
        right_scale = volume * spatial_volume * right_gain

        frame = int(source._playback_position)
        remaining = int(frame_count)
        output_index = 0

        while remaining > 0:
            if frame >= total_frames:
                if source.loop:
                    frame = 0
                    source._playback_position = 0.0
                    source._position = 0
                    reader.seek(0)
                else:
                    source._finish()
                    break

            cache_start = reader._cache_start
            cache_end = cache_start + reader._cache_frames

            if not cache_start <= frame < cache_end:
                reader._fill(frame)
                cache_start = reader._cache_start
                cache_end = cache_start + reader._cache_frames

            count = min(
                remaining,
                total_frames - frame,
                cache_end - frame,
            )

            if count <= 0:
                source._finish()
                break

            cache_frames = reader._cache.reshape(-1, source_channels)
            cache_offset = frame - cache_start
            chunk = cache_frames[cache_offset:cache_offset + count]
            out = output[output_index:output_index + count * 2].reshape(-1, 2)

            if source_channels == 1:
                mono = chunk[:, 0]
                out[:, 0] += mono * left_scale
                out[:, 1] += mono * right_scale
            else:
                out[:, 0] += chunk[:, 0] * left_scale
                out[:, 1] += chunk[:, 1] * right_scale

            output_index += count * 2

            frame += count
            remaining -= count
            source._playback_position = float(frame)
            source._position = frame

            if not source.loop and frame >= total_frames:
                source._finish()
                break

    # ==========================================================
    # CLAMP
    # ==========================================================

    @staticmethod
    def _clamp(
        samples: np.ndarray,
    ) -> None:
        np.clip(samples, -1.0, 1.0, out=samples)

    # ==========================================================
    # UPDATE
    # ==========================================================

    def _mix_frame_budget(
        self,
        active_source_count: int,
    ) -> int:
        """Return a mix budget that can keep up with a 30-FPS game loop.

        The mixer now has direct fast paths for ordinary PCM and sequential
        WAV streaming. The former 1024/1536-frame caps were meant to protect
        the old per-sample Python mixer, but at 30 FPS they produce less
        audio than the device consumes. That drains the queue exactly when
        voices, music and heartbeat are layered. ``max_update_frames`` still
        remains the caller's hard upper bound.
        """

        return self.max_update_frames

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

        with self._sources_lock:
            # Finished one-shot SFX/voices must not accumulate forever. Do
            # this before the early return below so a player containing only
            # stopped sources still releases them immediately.
            self._prune_stopped_sources_locked()
            active_source_count = sum(
                source.state == AudioSourceState.PLAYING
                for source in self._sources
            )

        if active_source_count <= 0:
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
            self._mix_frame_budget(active_source_count),
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
