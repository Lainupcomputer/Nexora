from __future__ import annotations

import ctypes
import math
import struct

import sdl3

from nexora.rendering.gpu.errors import decode_sdl_error

from nexora.rendering.gpu.buffer import GPUBuffer
from nexora.rendering.gpu.shader import GPUShader


_UNIT_QUAD_POSITIONS = struct.pack(
    "<12f",
    -0.5, -0.5,
     0.5, -0.5,
     0.5,  0.5,
    -0.5, -0.5,
     0.5,  0.5,
    -0.5,  0.5,
)

_UNIT_QUAD_POSITIONS_UV = struct.pack(
    "<24f",
    -0.5, -0.5, 0.0, 0.0,
     0.5, -0.5, 1.0, 0.0,
     0.5,  0.5, 1.0, 1.0,
    -0.5, -0.5, 0.0, 0.0,
     0.5,  0.5, 1.0, 1.0,
    -0.5,  0.5, 0.0, 1.0,
)


class GPUBatchCommonMixin:
    """Shared infrastructure used by Nexora's GPU batch renderers."""

    UNIT_QUAD_WITH_UV = False
    FRAGMENT_SHADER_SAMPLERS = 0

    def _create_resources(self) -> None:
        """Create the standard shader/quad/instance/pipeline resource set."""
        self._create_shaders()
        self._create_quad()
        self._create_instance_buffer()
        self._create_pipeline()

    def _create_shaders(self) -> None:
        """Create the standard vertex/fragment shader pair for a batch."""
        self.vertex_shader = GPUShader(
            self.device,
            self.vertex_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
            entrypoint="main",
            num_uniform_buffers=1,
        )
        self.fragment_shader = GPUShader(
            self.device,
            self.fragment_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
            entrypoint="main",
            num_samplers=int(self.FRAGMENT_SHADER_SAMPLERS),
        )

    def _create_quad(self) -> None:
        """Create the batch's standard centered unit quad."""
        self.quad_buffer = self._create_unit_quad_buffer(
            with_uv=bool(self.UNIT_QUAD_WITH_UV),
        )

    def _create_instance_buffer(self) -> None:
        """Create the dynamic instance buffer backed by ``_instance_data``."""
        self.instance_buffer = self._create_dynamic_vertex_buffer(
            len(self._instance_data)
        )

    def _create_static_vertex_buffer(self, data: bytes) -> GPUBuffer:
        """Create an immutable vertex buffer initialized with *data*."""
        return GPUBuffer(
            self.device,
            len(data),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            initial_data=data,
        )

    def _create_dynamic_vertex_buffer(self, size: int) -> GPUBuffer:
        """Create a triple-buffered dynamic vertex buffer."""
        return GPUBuffer(
            self.device,
            int(size),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            dynamic=True,
            frames_in_flight=3,
        )

    def _create_unit_quad_buffer(self, *, with_uv: bool = False) -> GPUBuffer:
        """Create Nexora's centered unit quad vertex buffer."""
        data = _UNIT_QUAD_POSITIONS_UV if with_uv else _UNIT_QUAD_POSITIONS
        return self._create_static_vertex_buffer(data)

    @staticmethod
    def _decode_error(error) -> str:
        return decode_sdl_error(error)

    def _check(self, condition, message: str) -> None:
        if condition:
            return
        error = self._decode_error(sdl3.SDL_GetError())
        raise RuntimeError(f"{message}: {error}")

    def _update_camera_uniform(self, *, screen_space: bool = False) -> None:
        if screen_space or self.camera is None:
            camera_x = 0.0
            camera_y = 0.0
            camera_zoom = 1.0
            shake_x = 0.0
            shake_y = 0.0
        else:
            camera_x = float(self.camera.x)
            camera_y = float(self.camera.y)
            camera_zoom = float(self.camera.zoom)
            shake_x = float(self.camera.shake_x)
            shake_y = float(self.camera.shake_y)

        viewport_width = float(self.context.swapchain_width)
        viewport_height = float(self.context.swapchain_height)

        struct.pack_into(
            "<8f",
            self._camera_data,
            0,
            camera_x,
            camera_y,
            viewport_width,
            viewport_height,
            camera_zoom,
            shake_x,
            shake_y,
            0.0,
        )

    def push_camera_uniform(self, command_buffer, *, screen_space: bool = False) -> None:
        self._update_camera_uniform(screen_space=screen_space)
        camera_buffer = (
            (ctypes.c_ubyte * self.CAMERA_UNIFORM_SIZE).from_buffer(self._camera_data)
        )
        sdl3.SDL_PushGPUVertexUniformData(
            command_buffer,
            0,
            ctypes.cast(camera_buffer, ctypes.c_void_p),
            self.CAMERA_UNIFORM_SIZE,
        )

    def _make_scissor_rect(self, clip_rect):
        """Convert Nexora centered screen coordinates to an SDL scissor rect."""
        viewport_width = max(int(self.context.swapchain_width), 0)
        viewport_height = max(int(self.context.swapchain_height), 0)

        if clip_rect is None:
            left = 0
            top = 0
            right = viewport_width
            bottom = viewport_height
        else:
            x, y, width, height = clip_rect
            half_width = viewport_width * 0.5
            half_height = viewport_height * 0.5
            left = math.floor(x + half_width)
            top = math.floor(y + half_height)
            right = math.ceil(x + width + half_width)
            bottom = math.ceil(y + height + half_height)
            left = max(0, min(left, viewport_width))
            top = max(0, min(top, viewport_height))
            right = max(left, min(right, viewport_width))
            bottom = max(top, min(bottom, viewport_height))

        rect = sdl3.SDL_Rect()
        rect.x = int(left)
        rect.y = int(top)
        rect.w = int(right - left)
        rect.h = int(bottom - top)
        return rect

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.destroy()
