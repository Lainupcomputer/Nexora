from __future__ import annotations

import ctypes
import struct
from pathlib import Path

import sdl3

from nexora.rendering.gpu.batch_common import GPUBatchCommonMixin


class GPURectBatch(GPUBatchCommonMixin):
    """
    GPU-instanced rectangle renderer.

    Each rectangle contains:

        position
        size
        rotation
        origin
        radius
        RGBA color

    The batch uses the same camera convention as GPUSpriteBatch:

        world origin = screen center
        +X = right
        +Y = down

    GPU / SDL operations must happen on the rendering thread.
    """

    MAX_RECTS = 50000

    INSTANCE_FLOATS = 12
    INSTANCE_STRIDE = 48

    CAMERA_UNIFORM_SIZE = 32

    def __init__(
        self,
        context,
        *,
        max_rects: int = 10000,
        vertex_shader_path,
        fragment_shader_path,
        camera=None,
    ):
        self.context = context
        self.device = context.device
        self.camera = camera

        self.max_rects = int(max_rects)

        if self.max_rects <= 0:
            raise ValueError(
                "max_rects must be greater than zero"
            )

        if self.max_rects > self.MAX_RECTS:
            raise ValueError(
                f"max_rects cannot exceed "
                f"{self.MAX_RECTS}"
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
            self.max_rects
            * self.INSTANCE_STRIDE
        )

        self._rect_count = 0

        # One clip rectangle per rectangle instance.
        #
        # Coordinates use Nexora's centered screen convention:
        #
        #     (0, 0) = viewport center
        #
        self._clip_rects: list[
            tuple[
                float,
                float,
                float,
                float,
            ] | None
        ] = []

        self._camera_data = bytearray(
            self.CAMERA_UNIFORM_SIZE
        )

        self._destroyed = False

        self._create_resources()

    # ==========================================================
    # ERROR
    # ==========================================================



    # ==========================================================
    # PIPELINE
    # ==========================================================

    def _create_pipeline(
        self,
    ):
        vertex_buffer_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription
            * 2
        )()

        # ------------------------------------------------------
        # Quad vertex buffer
        # ------------------------------------------------------

        vertex_buffer_descriptions[0].slot = 0

        vertex_buffer_descriptions[0].pitch = 8

        vertex_buffer_descriptions[0].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )

        vertex_buffer_descriptions[
            0
        ].instance_step_rate = 0

        # ------------------------------------------------------
        # Instance buffer
        # ------------------------------------------------------

        vertex_buffer_descriptions[1].slot = 1

        vertex_buffer_descriptions[
            1
        ].pitch = (
            self.INSTANCE_STRIDE
        )

        vertex_buffer_descriptions[
            1
        ].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_INSTANCE
        )

        vertex_buffer_descriptions[
            1
        ].instance_step_rate = 0

        # ------------------------------------------------------
        # Attributes
        #
        # Instance layout:
        #
        # 0  -  8 : position
        # 8  - 16 : size
        # 16 - 20 : rotation
        # 20 - 28 : origin
        # 28 - 32 : radius
        # 32 - 48 : color
        # ------------------------------------------------------

        attributes = (
            sdl3.SDL_GPUVertexAttribute
            * 7
        )()

        # ------------------------------------------------------
        # Quad position
        # ------------------------------------------------------

        attributes[0].location = 0
        attributes[0].buffer_slot = 0

        attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )

        attributes[0].offset = 0

        # ------------------------------------------------------
        # Instance position
        # ------------------------------------------------------

        attributes[1].location = 1
        attributes[1].buffer_slot = 1

        attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )

        attributes[1].offset = 0

        # ------------------------------------------------------
        # Instance size
        # ------------------------------------------------------

        attributes[2].location = 2
        attributes[2].buffer_slot = 1

        attributes[2].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )

        attributes[2].offset = 8

        # ------------------------------------------------------
        # Rotation
        # ------------------------------------------------------

        attributes[3].location = 3
        attributes[3].buffer_slot = 1

        attributes[3].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )

        attributes[3].offset = 16

        # ------------------------------------------------------
        # Origin
        # ------------------------------------------------------

        attributes[4].location = 4
        attributes[4].buffer_slot = 1

        attributes[4].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )

        attributes[4].offset = 20

        # ------------------------------------------------------
        # Radius
        # ------------------------------------------------------

        attributes[5].location = 5
        attributes[5].buffer_slot = 1

        attributes[5].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT
        )

        attributes[5].offset = 28

        # ------------------------------------------------------
        # Color
        # ------------------------------------------------------

        attributes[6].location = 6
        attributes[6].buffer_slot = 1

        attributes[6].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4
        )

        attributes[6].offset = 32

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

        multisample.enable_alpha_to_coverage = (
            False
        )

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

        color_target.blend_state.enable_blend = (
            True
        )

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

        color_target.blend_state.enable_color_write_mask = (
            True
        )

        color_target.blend_state.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        color_targets = (
            sdl3.SDL_GPUColorTargetDescription
            * 1
        )()

        color_targets[
            0
        ] = color_target

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

        target_info.has_depth_stencil_target = (
            False
        )

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

        vertex_input.vertex_attributes = (
            attributes
        )

        vertex_input.num_vertex_attributes = 7

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

        info.vertex_input_state = (
            vertex_input
        )

        info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        info.rasterizer_state = (
            rasterizer
        )

        info.multisample_state = (
            multisample
        )

        info.depth_stencil_state = (
            depth
        )

        info.target_info = (
            target_info
        )

        info.props = 0

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                ctypes.byref(
                    info
                ),
            )
        )

        self._check(
            self.pipeline,
            "SDL_CreateGPUGraphicsPipeline failed",
        )


    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def rect_count(
        self,
    ) -> int:
        return self._rect_count

    # ==========================================================
    # BEGIN
    # ==========================================================

    def begin(
        self,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPURectBatch has been destroyed"
            )

        self._rect_count = 0

        self._clip_rects.clear()

    # ==========================================================
    # ADD
    # ==========================================================

    def add(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        color=(
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        rotation: float = 0.0,
        origin=(
            0.5,
            0.5,
        ),
        radius: float = 0.0,
        clip_rect: tuple[
            float,
            float,
            float,
            float,
        ] | None = None,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPURectBatch has been destroyed"
            )

        if (
            self._rect_count
            >= self.max_rects
        ):
            raise RuntimeError(
                "GPURectBatch capacity exceeded "
                f"({self.max_rects} rectangles)"
            )

        self._write_instance(
            self._rect_count,
            x,
            y,
            width,
            height,
            rotation,
            origin,
            radius,
            color,
        )

        if clip_rect is None:
            self._clip_rects.append(
                None
            )

        else:
            (
                clip_x,
                clip_y,
                clip_w,
                clip_h,
            ) = clip_rect

            self._clip_rects.append(
                (
                    float(
                        clip_x
                    ),
                    float(
                        clip_y
                    ),
                    max(
                        float(
                            clip_w
                        ),
                        0.0,
                    ),
                    max(
                        float(
                            clip_h
                        ),
                        0.0,
                    ),
                )
            )

        self._rect_count += 1

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
        origin,
        radius: float,
        color,
    ):
        ox, oy = origin
        r, g, b, a = color

        offset = (
            index
            * self.INSTANCE_STRIDE
        )

        struct.pack_into(
            "<12f",
            self._instance_data,
            offset,
            float(
                x
            ),
            float(
                y
            ),
            float(
                width
            ),
            float(
                height
            ),
            float(
                rotation
            ),
            float(
                ox
            ),
            float(
                oy
            ),
            float(
                radius
            ),
            float(
                r
            ),
            float(
                g
            ),
            float(
                b
            ),
            float(
                a
            ),
        )

    # ==========================================================
    # CAMERA
    # ==========================================================



    # ==========================================================
    # RENDER INTO ACTIVE FRAME
    # ==========================================================

    def render_into(
        self,
        command_buffer,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPURectBatch has been destroyed"
            )

        if self._rect_count == 0:
            return 0

        # ------------------------------------------------------
        # Instance upload
        # ------------------------------------------------------

        instance_size = (
            self._rect_count
            * self.INSTANCE_STRIDE
        )

        self.instance_buffer.upload_into(
            command_buffer,
            memoryview(
                self._instance_data
            )[
                :instance_size
            ],
        )

        # ------------------------------------------------------
        # Camera
        # ------------------------------------------------------

        self._update_camera_uniform()

        camera_buffer = (
            (
                ctypes.c_ubyte
                * self.CAMERA_UNIFORM_SIZE
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

        return self._rect_count

    # ==========================================================
    # DRAW
    # ==========================================================

    def draw_into(
        self,
        render_pass,
    ):
        if self._destroyed:
            raise RuntimeError(
                "GPURectBatch has been destroyed"
            )

        if self._rect_count == 0:
            return 0

        # ------------------------------------------------------
        # Pipeline
        # ------------------------------------------------------

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self.pipeline,
        )

        # ------------------------------------------------------
        # Vertex buffers
        # ------------------------------------------------------

        instance_size = (
            self._rect_count
            * self.INSTANCE_STRIDE
        )

        vertex_bindings = (
            sdl3.SDL_GPUBufferBinding
            * 2
        )()

        vertex_bindings[
            0
        ] = self.quad_buffer.binding(
            0,
            self.quad_buffer.size,
        )

        vertex_bindings[
            1
        ] = self.instance_buffer.binding(
            0,
            instance_size,
        )

        sdl3.SDL_BindGPUVertexBuffers(
            render_pass,
            0,
            vertex_bindings,
            2,
        )

        # ------------------------------------------------------
        # Draw consecutive clip groups
        # ------------------------------------------------------
        #
        # Consecutive rectangles with the same clip rectangle are
        # emitted in one instanced draw call.
        #
        # This keeps ordering intact while allowing Scissor state
        # to change between groups.
        # ------------------------------------------------------

        drawn = 0

        run_start = 0

        while (
            run_start
            < self._rect_count
        ):
            clip_rect = (
                self._clip_rects[
                    run_start
                ]
            )

            run_end = (
                run_start
                + 1
            )

            while (
                run_end
                < self._rect_count
                and self._clip_rects[
                    run_end
                ]
                == clip_rect
            ):
                run_end += 1

            scissor = (
                self._make_scissor_rect(
                    clip_rect
                )
            )

            # Empty intersection:
            # nothing to draw.
            if (
                scissor.w > 0
                and scissor.h > 0
            ):
                sdl3.SDL_SetGPUScissor(
                    render_pass,
                    ctypes.byref(
                        scissor
                    ),
                )

                run_count = (
                    run_end
                    - run_start
                )

                sdl3.SDL_DrawGPUPrimitives(
                    render_pass,
                    6,
                    run_count,
                    0,
                    run_start,
                )

                drawn += (
                    run_count
                )

            run_start = (
                run_end
            )

        # ------------------------------------------------------
        # Restore effectively unclipped state
        # ------------------------------------------------------

        full_scissor = (
            self._make_scissor_rect(
                None
            )
        )

        sdl3.SDL_SetGPUScissor(
            render_pass,
            ctypes.byref(
                full_scissor
            ),
        )

        return drawn


    # ==========================================================
    # Draw range
    # ==========================================================

    def draw_range(
        self,
        render_pass,
        start: int,
        count: int,
    ) -> int:
        """
        Draw a contiguous range of already uploaded rectangle
        instances.
        """

        if self._destroyed:
            raise RuntimeError(
                "GPURectBatch has been destroyed"
            )

        start = int(start)
        count = int(count)

        if count <= 0:
            return 0

        if start < 0:
            raise ValueError(
                "start must be greater than or equal to zero"
            )

        end = start + count

        if end > self._rect_count:
            raise ValueError(
                "Rectangle draw range exceeds current batch "
                f"({end} > {self._rect_count})"
            )

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self.pipeline,
        )

        instance_size = (
            self._rect_count
            * self.INSTANCE_STRIDE
        )

        vertex_bindings = (
            sdl3.SDL_GPUBufferBinding
            * 2
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

        drawn = 0
        run_start = start

        while run_start < end:
            clip_rect = (
                self._clip_rects[
                    run_start
                ]
            )

            run_end = (
                run_start
                + 1
            )

            while (
                run_end
                < end
                and self._clip_rects[
                    run_end
                ] == clip_rect
            ):
                run_end += 1

            scissor = (
                self._make_scissor_rect(
                    clip_rect
                )
            )

            if (
                scissor.w > 0
                and scissor.h > 0
            ):
                sdl3.SDL_SetGPUScissor(
                    render_pass,
                    ctypes.byref(
                        scissor
                    ),
                )

                run_count = (
                    run_end
                    - run_start
                )

                sdl3.SDL_DrawGPUPrimitives(
                    render_pass,
                    6,
                    run_count,
                    0,
                    run_start,
                )

                drawn += run_count

            run_start = run_end

        full_scissor = (
            self._make_scissor_rect(
                None
            )
        )

        sdl3.SDL_SetGPUScissor(
            render_pass,
            ctypes.byref(
                full_scissor
            ),
        )

        return drawn

    # ==========================================================
    # SCISSOR
    # ==========================================================


    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(
        self,
    ):
        self._rect_count = 0

        self._clip_rects.clear()

    # ==========================================================
    # DESTROY
    # ==========================================================

    def destroy(
        self,
    ):
        if self._destroyed:
            return

        self._destroyed = True

        try:
            self.context.wait_idle()

        except Exception:
            pass

        # ------------------------------------------------------
        # Pipeline
        # ------------------------------------------------------

        if self.pipeline:
            try:
                sdl3.SDL_ReleaseGPUGraphicsPipeline(
                    self.device,
                    self.pipeline,
                )

            except Exception:
                pass

            self.pipeline = None

        # ------------------------------------------------------
        # Instance buffer
        # ------------------------------------------------------

        if self.instance_buffer:
            try:
                self.instance_buffer.destroy()

            except Exception:
                pass

            self.instance_buffer = None

        # ------------------------------------------------------
        # Quad buffer
        # ------------------------------------------------------

        if self.quad_buffer:
            try:
                self.quad_buffer.destroy()

            except Exception:
                pass

            self.quad_buffer = None

        # ------------------------------------------------------
        # Shaders
        # ------------------------------------------------------

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

        self._instance_data = (
            bytearray()
        )

        self._clip_rects.clear()

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================


