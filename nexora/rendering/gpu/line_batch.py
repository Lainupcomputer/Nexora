from __future__ import annotations

import ctypes
import math
import struct
from pathlib import Path

import sdl3

from nexora.rendering.gpu.buffer import GPUBuffer
from nexora.rendering.gpu.shader import GPUShader


class GPULineBatch:
    """
    GPU-instanced line renderer.

    Lines are rendered as rotated quads.

    Coordinate system:

        world origin = screen center
        +X = right
        +Y = down

    GPU / SDL operations must happen on the rendering thread.
    """

    MAX_LINES = 50000

    # position x/y
    # size x/y
    # rotation
    # origin x/y
    # color r/g/b/a
    INSTANCE_FLOATS = 11
    INSTANCE_STRIDE = 44

    CAMERA_UNIFORM_SIZE = 32

    def __init__(
        self,
        context,
        *,
        max_lines: int = 10000,
        vertex_shader_path,
        fragment_shader_path,
        camera=None,
    ):
        self.context = context
        self.device = context.device
        self.camera = camera

        self.max_lines = int(max_lines)

        if self.max_lines <= 0:
            raise ValueError(
                "max_lines must be greater than zero"
            )

        if self.max_lines > self.MAX_LINES:
            raise ValueError(
                f"max_lines cannot exceed "
                f"{self.MAX_LINES}"
            )

        self.vertex_shader_path = Path(
            vertex_shader_path
        )

        self.fragment_shader_path = Path(
            fragment_shader_path
        )

        # ------------------------------------------------------
        # GPU resources
        # ------------------------------------------------------

        self.vertex_shader = None
        self.fragment_shader = None

        self.quad_buffer = None
        self.instance_buffer = None
        self.pipeline = None

        # ------------------------------------------------------
        # CPU instance storage
        # ------------------------------------------------------

        self._instance_data = bytearray(
            self.max_lines
            * self.INSTANCE_STRIDE
        )

        self._line_count = 0

        self._camera_data = bytearray(
            self.CAMERA_UNIFORM_SIZE
        )

        self._destroyed = False

        self._create_resources()

    # ==========================================================
    # ERROR
    # ==========================================================

    @staticmethod
    def _decode_error(error) -> str:
        if isinstance(error, bytes):
            return error.decode(
                "utf-8",
                errors="replace",
            )

        if error is None:
            return "<unknown SDL error>"

        return str(error)

    def _check(self, condition, message):
        if not condition:
            error = self._decode_error(
                sdl3.SDL_GetError()
            )

            raise RuntimeError(
                f"{message}: {error}"
            )

    # ==========================================================
    # RESOURCE CREATION
    # ==========================================================

    def _create_resources(self):
        self._create_shaders()
        self._create_quad()
        self._create_instance_buffer()
        self._create_pipeline()

    # ==========================================================
    # SHADERS
    # ==========================================================

    def _create_shaders(self):
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
        )

    # ==========================================================
    # QUAD
    # ==========================================================

    def _create_quad(self):
        """
        Unit quad.

        Six vertices = two triangles.

        Position range:

            -0.5 ... +0.5
        """

        vertices = struct.pack(
            "<12f",

            # Triangle 1
            -0.5, -0.5,
             0.5, -0.5,
             0.5,  0.5,

            # Triangle 2
            -0.5, -0.5,
             0.5,  0.5,
            -0.5,  0.5,
        )

        self.quad_buffer = GPUBuffer(
            self.device,
            len(vertices),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            initial_data=vertices,
        )

    # ==========================================================
    # INSTANCE BUFFER
    # ==========================================================

    def _create_instance_buffer(self):
        self.instance_buffer = GPUBuffer(
            self.device,
            len(self._instance_data),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            dynamic=True,
            frames_in_flight=3,
        )

    # ==========================================================
    # PIPELINE
    # ==========================================================

    def _create_pipeline(self):
        vertex_buffer_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription * 2
        )()

        # ------------------------------------------------------
        # Quad
        # ------------------------------------------------------

        vertex_buffer_descriptions[0].slot = 0

        vertex_buffer_descriptions[0].pitch = 8

        vertex_buffer_descriptions[0].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )

        vertex_buffer_descriptions[0].instance_step_rate = 0

        # ------------------------------------------------------
        # Instance
        # ------------------------------------------------------

        vertex_buffer_descriptions[1].slot = 1

        vertex_buffer_descriptions[1].pitch = (
            self.INSTANCE_STRIDE
        )

        vertex_buffer_descriptions[1].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_INSTANCE
        )

        vertex_buffer_descriptions[1].instance_step_rate = 0

        # ------------------------------------------------------
        # Attributes
        # ------------------------------------------------------

        attributes = (
            sdl3.SDL_GPUVertexAttribute * 6
        )()

        # Quad position
        attributes[0].location = 0
        attributes[0].buffer_slot = 0
        attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[0].offset = 0

        # Position
        attributes[1].location = 1
        attributes[1].buffer_slot = 1
        attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[1].offset = 0

        # Size
        attributes[2].location = 2
        attributes[2].buffer_slot = 1
        attributes[2].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[2].offset = 8

        # Rotation
        attributes[3].location = 3
        attributes[3].buffer_slot = 1
        attributes[3].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )
        attributes[3].offset = 16

        # Origin
        attributes[4].location = 4
        attributes[4].buffer_slot = 1
        attributes[4].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[4].offset = 20

        # Color
        attributes[5].location = 5
        attributes[5].buffer_slot = 1
        attributes[5].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4
        )
        attributes[5].offset = 28

        # ------------------------------------------------------
        # Rasterizer
        # ------------------------------------------------------

        rasterizer = (
            sdl3.SDL_GPURasterizerState()
        )

        rasterizer.fill_mode = (
            sdl3.SDL_GPU_FILLMODE_FILL
        )

        rasterizer.cull_mode = (
            sdl3.SDL_GPU_CULLMODE_NONE
        )

        rasterizer.front_face = (
            sdl3.SDL_GPU_FRONTFACE_COUNTER_CLOCKWISE
        )

        rasterizer.enable_depth_bias = False
        rasterizer.enable_depth_clip = True

        # ------------------------------------------------------
        # Multisample
        # ------------------------------------------------------

        multisample = (
            sdl3.SDL_GPUMultisampleState()
        )

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False
        multisample.enable_alpha_to_coverage = False

        # ------------------------------------------------------
        # Depth
        # ------------------------------------------------------

        depth = (
            sdl3.SDL_GPUDepthStencilState()
        )

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        # ------------------------------------------------------
        # Color target
        # ------------------------------------------------------

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = (
            self.context.swapchain_format
        )

        # ------------------------------------------------------
        # Alpha blending
        # ------------------------------------------------------

        color_target.blend_state.enable_blend = True

        color_target.blend_state.src_color_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_SRC_ALPHA
        )

        color_target.blend_state.dst_color_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA
        )

        color_target.blend_state.color_blend_op = (
            sdl3.SDL_GPU_BLENDOP_ADD
        )

        color_target.blend_state.src_alpha_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE
        )

        color_target.blend_state.dst_alpha_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA
        )

        color_target.blend_state.alpha_blend_op = (
            sdl3.SDL_GPU_BLENDOP_ADD
        )

        color_target.blend_state.enable_color_write_mask = True

        color_target.blend_state.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        color_targets = (
            sdl3.SDL_GPUColorTargetDescription * 1
        )()

        color_targets[0] = color_target

        # ------------------------------------------------------
        # Target info
        # ------------------------------------------------------

        target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        target_info.color_target_descriptions = (
            color_targets
        )

        target_info.num_color_targets = 1

        target_info.depth_stencil_format = 0
        target_info.has_depth_stencil_target = False

        # ------------------------------------------------------
        # Vertex input
        # ------------------------------------------------------

        vertex_input = (
            sdl3.SDL_GPUVertexInputState()
        )

        vertex_input.vertex_buffer_descriptions = (
            vertex_buffer_descriptions
        )

        vertex_input.num_vertex_buffers = 2

        vertex_input.vertex_attributes = attributes
        vertex_input.num_vertex_attributes = 6

        # ------------------------------------------------------
        # Pipeline
        # ------------------------------------------------------

        info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        info.vertex_shader = (
            self.vertex_shader.shader
        )

        info.fragment_shader = (
            self.fragment_shader.shader
        )

        info.vertex_input_state = vertex_input

        info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        info.rasterizer_state = rasterizer
        info.multisample_state = multisample
        info.depth_stencil_state = depth
        info.target_info = target_info
        info.props = 0

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                ctypes.byref(info),
            )
        )

        self._check(
            self.pipeline,
            "SDL_CreateGPUGraphicsPipeline failed",
        )

    # ==========================================================
    # BEGIN
    # ==========================================================

    def begin(self):
        if self._destroyed:
            raise RuntimeError(
                "GPULineBatch has been destroyed"
            )

        self._line_count = 0

    # ==========================================================
    # ADD
    # ==========================================================

    def add(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        width: float = 1.0,
        color=(1.0, 1.0, 1.0, 1.0),
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPULineBatch has been destroyed"
            )

        if self._line_count >= self.max_lines:
            raise RuntimeError(
                "GPULineBatch capacity exceeded "
                f"({self.max_lines} lines)"
            )

        dx = float(x2) - float(x1)
        dy = float(y2) - float(y1)

        length = math.sqrt(
            dx * dx +
            dy * dy
        )

        # Degenerate line
        if length <= 0.000001:
            rotation = 0.0
        else:
            rotation = math.atan2(
                dy,
                dx,
            )

        center_x = (
            float(x1) +
            float(x2)
        ) * 0.5

        center_y = (
            float(y1) +
            float(y2)
        ) * 0.5

        self._write_instance(
            self._line_count,
            center_x,
            center_y,
            length,
            float(width),
            rotation,
            color,
        )

        self._line_count += 1

    # ==========================================================
    # WRITE INSTANCE
    # ==========================================================

    def _write_instance(
        self,
        index: int,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float,
        color,
    ):
        offset = (
            index *
            self.INSTANCE_STRIDE
        )

        struct.pack_into(
            "<11f",
            self._instance_data,
            offset,

            float(x),
            float(y),

            float(width),
            float(height),

            float(rotation),

            0.5,
            0.5,

            float(color[0]),
            float(color[1]),
            float(color[2]),
            float(color[3]),
        )

    # ==========================================================
    # CAMERA
    # ==========================================================

    def _update_camera_uniform(self):
        if self.camera is None:
            camera_x = 0.0
            camera_y = 0.0
            camera_zoom = 1.0
            shake_x = 0.0
            shake_y = 0.0

        else:
            camera_x = float(
                self.camera.x
            )

            camera_y = float(
                self.camera.y
            )

            camera_zoom = float(
                self.camera.zoom
            )

            shake_x = float(
                self.camera.shake_x
            )

            shake_y = float(
                self.camera.shake_y
            )

        viewport_width = float(
            self.context.swapchain_width
        )

        viewport_height = float(
            self.context.swapchain_height
        )

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

    # ==========================================================
    # RENDER
    # ==========================================================

    def render_into(self, command_buffer):
        if self._destroyed:
            raise RuntimeError(
                "GPULineBatch has been destroyed"
            )

        if self._line_count == 0:
            return 0

        instance_size = (
            self._line_count *
            self.INSTANCE_STRIDE
        )

        self.instance_buffer.upload_into(
            command_buffer,
            memoryview(
                self._instance_data
            )[:instance_size],
        )

        self._update_camera_uniform()

        camera_buffer = (
            (
                ctypes.c_ubyte *
                self.CAMERA_UNIFORM_SIZE
            ).from_buffer(
                self._camera_data
            )
        )

        sdl3.SDL_PushGPUVertexUniformData(
            command_buffer,
            0,
            ctypes.cast(
                camera_buffer,
                ctypes.c_void_p,
            ),
            self.CAMERA_UNIFORM_SIZE,
        )

        return self._line_count

    # ==========================================================
    # DRAW
    # ==========================================================

    def draw_into(self, render_pass):
        if self._destroyed:
            raise RuntimeError(
                "GPULineBatch has been destroyed"
            )

        if self._line_count == 0:
            return 0

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self.pipeline,
        )

        instance_size = (
            self._line_count *
            self.INSTANCE_STRIDE
        )

        vertex_bindings = (
            sdl3.SDL_GPUBufferBinding * 2
        )()

        vertex_bindings[0] = (
            self.quad_buffer.binding(
                0,
                self.quad_buffer.size,
            )
        )

        vertex_bindings[1] = (
            self.instance_buffer.binding(
                0,
                instance_size,
            )
        )

        sdl3.SDL_BindGPUVertexBuffers(
            render_pass,
            0,
            vertex_bindings,
            2,
        )

        sdl3.SDL_DrawGPUPrimitives(
            render_pass,
            6,
            self._line_count,
            0,
            0,
        )

        return self._line_count

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self):
        self._line_count = 0

    # ==========================================================
    # DESTROY
    # ==========================================================

    def destroy(self):
        if self._destroyed:
            return

        self._destroyed = True

        try:
            self.context.wait_idle()
        except Exception:
            pass

        if self.pipeline:
            try:
                sdl3.SDL_ReleaseGPUGraphicsPipeline(
                    self.device,
                    self.pipeline,
                )
            except Exception:
                pass

            self.pipeline = None

        if self.instance_buffer:
            try:
                self.instance_buffer.destroy()
            except Exception:
                pass

            self.instance_buffer = None

        if self.quad_buffer:
            try:
                self.quad_buffer.destroy()
            except Exception:
                pass

            self.quad_buffer = None

        if self.vertex_shader:
            try:
                self.vertex_shader.destroy()
            except Exception:
                pass

            self.vertex_shader = None

        if self.fragment_shader:
            try:
                self.fragment_shader.destroy()
            except Exception:
                pass

            self.fragment_shader = None

        self._instance_data = bytearray()

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()