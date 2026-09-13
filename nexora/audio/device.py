from __future__ import annotations

import ctypes

import sdl3


class AudioDevice:
    """Low-level SDL3 audio output device."""

    DEFAULT_FREQUENCY = 48_000
    DEFAULT_CHANNELS = 2

    def __init__(
        self,
        *,
        frequency: int = DEFAULT_FREQUENCY,
        channels: int = DEFAULT_CHANNELS,
    ) -> None:
        self.frequency = frequency
        self.channels = channels

        self._stream = None
        self._device_id = None
        self._initialized = False
        self._callback = None
        self._audio_subsystem_initialized = False
        self._data_provider = None

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def device_id(self):
        return self._device_id

    @property
    def stream(self):
        return self._stream

    @staticmethod
    def _audio_callback(
        stream,
        additional_amount,
        total_amount,
        userdata,
    ) -> None:
        if userdata is None:
            return
        
    def set_data_provider(self, provider) -> None:
        """Set the callback used to provide audio data."""

        self._data_provider = provider


    @staticmethod
    def _get_error() -> str:
        error = sdl3.SDL_GetError()

        if isinstance(error, bytes):
            return error.decode(
                "utf-8",
                errors="replace",
            )

        return str(error)

    def initialize(self) -> None:
        if self._initialized:
            return

        if not sdl3.SDL_InitSubSystem(sdl3.SDL_INIT_AUDIO):
            raise RuntimeError(
                "Failed to initialize SDL3 audio subsystem: "
                f"{self._get_error()}"
            )

        self._audio_subsystem_initialized = True

        spec = sdl3.SDL_AudioSpec()

        spec.freq = self.frequency
        spec.channels = self.channels
        spec.format = sdl3.SDL_AUDIO_F32

        self._callback = sdl3.SDL_AudioStreamCallback(
            self._audio_callback
        )

        stream = sdl3.SDL_OpenAudioDeviceStream(
            sdl3.SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK,
            ctypes.byref(spec),
            self._callback,
            None,
        )

        if not stream:
            self._callback = None

            if self._audio_subsystem_initialized:
                sdl3.SDL_QuitSubSystem(
                    sdl3.SDL_INIT_AUDIO
                )

                self._audio_subsystem_initialized = False

            raise RuntimeError(
                "Failed to open SDL3 audio device: "
                f"{self._get_error()}"
            )

        self._stream = stream
        self._device_id = sdl3.SDL_GetAudioStreamDevice(
            stream
        )

        if not sdl3.SDL_ResumeAudioStreamDevice(stream):
            sdl3.SDL_DestroyAudioStream(stream)

            self._stream = None
            self._device_id = None
            self._callback = None

            if self._audio_subsystem_initialized:
                sdl3.SDL_QuitSubSystem(
                    sdl3.SDL_INIT_AUDIO
                )

                self._audio_subsystem_initialized = False

            raise RuntimeError(
                "Failed to resume SDL3 audio device: "
                f"{self._get_error()}"
            )

        self._initialized = True

    def pause(self) -> None:
        if not self._initialized:
            return

        if not sdl3.SDL_PauseAudioStreamDevice(
            self._stream
        ):
            raise RuntimeError(
                "Failed to pause SDL3 audio device: "
                f"{self._get_error()}"
            )

    def resume(self) -> None:
        if not self._initialized:
            return

        if not sdl3.SDL_ResumeAudioStreamDevice(
            self._stream
        ):
            raise RuntimeError(
                "Failed to resume SDL3 audio device: "
                f"{self._get_error()}"
            )

    def shutdown(self) -> None:
        if self._stream is not None:
            sdl3.SDL_DestroyAudioStream(
                self._stream
            )

        self._stream = None
        self._device_id = None
        self._callback = None
        self._initialized = False

        if self._audio_subsystem_initialized:
            sdl3.SDL_QuitSubSystem(
                sdl3.SDL_INIT_AUDIO
            )

            self._audio_subsystem_initialized = False

    def write(self, data: bytes) -> None:
        """Write PCM audio data to the output stream."""

        if not self._initialized:
            raise RuntimeError(
                "Audio device is not initialized."
            )

        if not data:
            return

        if not sdl3.SDL_PutAudioStreamData(
            self._stream,
            data,
            len(data),
        ):
            raise RuntimeError(
                "Failed to write audio data: "
                f"{self._get_error()}"
            )