from __future__ import annotations

import ctypes

import sdl3


class AudioDevice:
    """
    Low-level SDL3 audio output device.

    Nexora uses SDL_AudioStream in push mode:

        AudioPlayer
            -> mix PCM
            -> SDL_PutAudioStreamData()

    PySDL3 currently expects a real SDL_AudioStreamCallback
    instance when opening the stream, so a no-op callback is
    kept alive even though audio data is pushed manually.

    The queue depth can be queried so AudioPlayer only produces
    as much audio as the device actually needs.
    """

    DEFAULT_FREQUENCY = 48_000
    DEFAULT_CHANNELS = 2

    BYTES_PER_SAMPLE = 4

    def __init__(
        self,
        *,
        frequency: int = DEFAULT_FREQUENCY,
        channels: int = DEFAULT_CHANNELS,
    ) -> None:
        self.frequency = int(
            frequency
        )

        self.channels = int(
            channels
        )

        if self.frequency <= 0:
            raise ValueError(
                "frequency must be greater than zero"
            )

        if self.channels <= 0:
            raise ValueError(
                "channels must be greater than zero"
            )

        self._stream = None
        self._device_id = None

        self._callback = None

        self._initialized = False

        self._audio_subsystem_initialized = (
            False
        )

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def initialized(
        self,
    ) -> bool:
        return self._initialized

    @property
    def device_id(
        self,
    ):
        return self._device_id

    @property
    def stream(
        self,
    ):
        return self._stream

    @property
    def frame_size(
        self,
    ) -> int:
        """
        Size of one interleaved PCM frame in bytes.

        Nexora currently outputs float32 samples.
        """

        return (
            self.channels
            * self.BYTES_PER_SAMPLE
        )

    # ==========================================================
    # ERROR HANDLING
    # ==========================================================

    @staticmethod
    def _get_error(
        error=None,
    ) -> str:
        if error is None:
            error = (
                sdl3.SDL_GetError()
            )

        if isinstance(
            error,
            bytes,
        ):
            return error.decode(
                "utf-8",
                errors="replace",
            )

        if error is None:
            return "<unknown SDL error>"

        return str(
            error
        )

    @classmethod
    def _check(
        cls,
        condition,
        message: str,
    ) -> None:
        if condition:
            return

        raise RuntimeError(
            f"{message}: "
            f"{cls._get_error()}"
        )

    # ==========================================================
    # AUDIO CALLBACK
    # ==========================================================

    @staticmethod
    def _audio_callback(
        stream,
        additional_amount,
        total_amount,
        userdata,
    ) -> None:
        """
        No-op callback.

        Audio data is supplied manually by AudioPlayer via
        SDL_PutAudioStreamData().

        PySDL3 currently requires an SDL_AudioStreamCallback
        instance instead of accepting None directly.
        """

        return

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        if self._initialized:
            return

        # ------------------------------------------------------
        # SDL audio subsystem
        # ------------------------------------------------------

        self._check(
            sdl3.SDL_InitSubSystem(
                sdl3.SDL_INIT_AUDIO
            ),
            "Failed to initialize SDL3 audio subsystem",
        )

        self._audio_subsystem_initialized = (
            True
        )

        try:
            # --------------------------------------------------
            # Desired output format
            # --------------------------------------------------

            spec = (
                sdl3.SDL_AudioSpec()
            )

            spec.freq = (
                self.frequency
            )

            spec.channels = (
                self.channels
            )

            spec.format = (
                sdl3.SDL_AUDIO_F32
            )

            # --------------------------------------------------
            # PySDL3 callback wrapper
            # --------------------------------------------------

            self._callback = (
                sdl3.SDL_AudioStreamCallback(
                    self._audio_callback
                )
            )

            # --------------------------------------------------
            # Open output stream
            # --------------------------------------------------

            self._stream = (
                sdl3.SDL_OpenAudioDeviceStream(
                    sdl3.SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK,
                    ctypes.byref(
                        spec
                    ),
                    self._callback,
                    None,
                )
            )

            self._check(
                self._stream,
                "Failed to open SDL3 audio device",
            )

            # --------------------------------------------------
            # Resolve actual device
            # --------------------------------------------------

            self._device_id = (
                sdl3.SDL_GetAudioStreamDevice(
                    self._stream
                )
            )

            # --------------------------------------------------
            # Start playback
            # --------------------------------------------------

            self._check(
                sdl3.SDL_ResumeAudioStreamDevice(
                    self._stream
                ),
                "Failed to resume SDL3 audio device",
            )

            self._initialized = True

        except Exception:
            self.shutdown()
            raise

    # ==========================================================
    # QUEUE
    # ==========================================================

    def queued_bytes(
        self,
    ) -> int:
        """
        Return the number of bytes currently queued in the
        SDL audio stream.
        """

        if not self._initialized:
            return 0

        if self._stream is None:
            return 0

        queued = (
            sdl3.SDL_GetAudioStreamQueued(
                self._stream
            )
        )

        if queued < 0:
            raise RuntimeError(
                "Failed to query SDL3 audio queue: "
                f"{self._get_error()}"
            )

        return int(
            queued
        )

    def queued_frames(
        self,
    ) -> int:
        """
        Return the approximate number of PCM frames currently
        queued in the SDL audio stream.
        """

        frame_size = (
            self.frame_size
        )

        if frame_size <= 0:
            return 0

        return (
            self.queued_bytes()
            // frame_size
        )

    def clear(
        self,
    ) -> None:
        """
        Remove all pending audio from the stream.
        """

        if not self._initialized:
            return

        if self._stream is None:
            return

        self._check(
            sdl3.SDL_ClearAudioStream(
                self._stream
            ),
            "Failed to clear SDL3 audio stream",
        )

    # ==========================================================
    # PAUSE / RESUME
    # ==========================================================

    def pause(
        self,
    ) -> None:
        if not self._initialized:
            return

        if self._stream is None:
            return

        self._check(
            sdl3.SDL_PauseAudioStreamDevice(
                self._stream
            ),
            "Failed to pause SDL3 audio device",
        )

    def resume(
        self,
    ) -> None:
        if not self._initialized:
            return

        if self._stream is None:
            return

        self._check(
            sdl3.SDL_ResumeAudioStreamDevice(
                self._stream
            ),
            "Failed to resume SDL3 audio device",
        )

    # ==========================================================
    # WRITE
    # ==========================================================

    def write(
        self,
        data: bytes,
    ) -> None:
        """
        Queue PCM data for playback.
        """

        if not self._initialized:
            raise RuntimeError(
                "Audio device is not initialized."
            )

        if self._stream is None:
            raise RuntimeError(
                "Audio stream is not initialized."
            )

        if not data:
            return

        self._check(
            sdl3.SDL_PutAudioStreamData(
                self._stream,
                data,
                len(
                    data
                ),
            ),
            "Failed to write audio data",
        )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Destroy stream
        # ------------------------------------------------------

        if self._stream is not None:
            try:
                sdl3.SDL_DestroyAudioStream(
                    self._stream
                )

            except Exception:
                pass

        self._stream = None
        self._device_id = None

        # Keep callback alive until after the stream is gone.
        self._callback = None

        self._initialized = False

        # ------------------------------------------------------
        # SDL audio subsystem
        # ------------------------------------------------------

        if self._audio_subsystem_initialized:
            try:
                sdl3.SDL_QuitSubSystem(
                    sdl3.SDL_INIT_AUDIO
                )

            except Exception:
                pass

            self._audio_subsystem_initialized = (
                False
            )

    # ==========================================================
    # DESTROY ALIAS
    # ==========================================================

    def destroy(
        self,
    ) -> None:
        self.shutdown()

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(
        self,
    ):
        self.initialize()

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.shutdown()