from __future__ import annotations

import ctypes
from pathlib import Path

import sdl3


class GPUShader:
    """
    SDL_GPU shader resource.

    Currently supports DXIL, SPIR-V and MSL depending on the
    supplied shader format.
    """

    def __init__(
        self,
        device,
        path: str | Path,
        stage,
        shader_format=None,
        *,
        entrypoint: str = "main",
        num_samplers: int = 0,
        num_storage_textures: int = 0,
        num_storage_buffers: int = 0,
        num_uniform_buffers: int = 0,
    ):
        self.device = device
        self.path = Path(path)
        self.stage = stage

        if shader_format is None:
            shader_format = sdl3.SDL_GPU_SHADERFORMAT_DXIL

        self.format = shader_format
        self.entrypoint = entrypoint

        self.shader = None

        # Keep these alive for the lifetime of SDL_CreateGPUShader.
        self._data = None
        self._buffer = None

        self._create(
            num_samplers=num_samplers,
            num_storage_textures=num_storage_textures,
            num_storage_buffers=num_storage_buffers,
            num_uniform_buffers=num_uniform_buffers,
        )

    def _create(
        self,
        *,
        num_samplers: int,
        num_storage_textures: int,
        num_storage_buffers: int,
        num_uniform_buffers: int,
    ) -> None:
        self._data = self.path.read_bytes()

        if not self._data:
            raise RuntimeError(
                f"Shader is empty: {self.path}"
            )

        self._buffer = (
            ctypes.c_ubyte * len(self._data)
        ).from_buffer_copy(self._data)

        info = sdl3.SDL_GPUShaderCreateInfo()

        info.code_size = len(self._data)

        info.code = ctypes.cast(
            self._buffer,
            ctypes.POINTER(ctypes.c_ubyte),
        )

        info.entrypoint = self.entrypoint.encode(
            "utf-8"
        )

        info.format = self.format
        info.stage = self.stage

        info.num_samplers = num_samplers
        info.num_storage_textures = (
            num_storage_textures
        )
        info.num_storage_buffers = (
            num_storage_buffers
        )
        info.num_uniform_buffers = (
            num_uniform_buffers
        )

        info.props = 0

        self.shader = sdl3.SDL_CreateGPUShader(
            self.device,
            ctypes.byref(info),
        )

        if not self.shader:
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"SDL_CreateGPUShader failed "
                f"for {self.path}: {error}"
            )

    def destroy(self) -> None:
        if self.shader:
            sdl3.SDL_ReleaseGPUShader(
                self.device,
                self.shader,
            )

            self.shader = None

        self._buffer = None
        self._data = None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()