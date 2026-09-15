
from __future__ import annotations

import ctypes
import math
import struct
from pathlib import Path

import sdl3

from nexora.rendering.text import Font
from nexora.rendering.gpu.buffer import GPUBuffer
from nexora.rendering.gpu.sampler import GPUSampler
from nexora.rendering.gpu.shader import GPUShader
from nexora.rendering.gpu.font_atlas import GPUFontAtlas


INSTANCE_FLOATS = 14
INSTANCE_STRIDE = INSTANCE_FLOATS * 4

CAMERA_UNIFORM_SIZE = 8 * 4
TEXT_COLOR_UNIFORM_SIZE = 4 * 4

DEFAULT_MAX_GLYPHS = 10_000


class GPUTextRenderer:
    """
    GPU text renderer based on SDL_ttf and a GPU font atlas.

    SDL_ttf rasterizes the glyphs on the CPU.
    GPUFontAtlas stores the resulting glyph images in one GPU texture.

    Each character is rendered as one instance of a static quad.

    Shader paths are supplied by the owning GPURenderer so the
    renderer does not depend on a hard-coded engine shader path.
    """

    def __init__(
        self,
        context,
        font: Font,
        *,
        vertex_shader_path: str | Path,
        fragment_shader_path: str | Path,
        atlas_width: int = 1024,
        atlas_height: int = 1024,
        atlas_padding: int = 2,
        charset: str | None = None,
        max_glyphs: int = DEFAULT_MAX_GLYPHS,
    ) -> None:
        self.context = context
        self.device = context.device
        self.font = font

        # ======================================================
        # Limits
        # ======================================================

        self.max_glyphs = int(
            max_glyphs
        )

        if self.max_glyphs <= 0:
            raise ValueError(
                "max_glyphs must be greater than zero."
            )

        # ======================================================
        # Shader paths
        # ======================================================

        self.vertex_shader_path = Path(
            vertex_shader_path
        )

        self.fragment_shader_path = Path(
            fragment_shader_path
        )

        if not self.vertex_shader_path.is_file():
            raise FileNotFoundError(
                "Text vertex shader not found: "
                f"{self.vertex_shader_path}"
            )

        if not self.fragment_shader_path.is_file():
            raise FileNotFoundError(
                "Text fragment shader not found: "
                f"{self.fragment_shader_path}"
            )

        # ======================================================
        # Font atlas
        # ======================================================

        self.atlas = GPUFontAtlas(
            self.device,
            font,
            width=atlas_width,
            height=atlas_height,
            padding=atlas_padding,
            charset=charset,
        )

        # ======================================================
        # Shaders
        # ======================================================

        self._vertex_shader = GPUShader(
            self.device,
            self.vertex_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
            shader_format=(
                sdl3.SDL_GPU_SHADERFORMAT_SPIRV
            ),
            num_uniform_buffers=1,
        )

        self._fragment_shader = GPUShader(
            self.device,
            self.fragment_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
            shader_format=(
                sdl3.SDL_GPU_SHADERFORMAT_SPIRV
            ),
            num_samplers=1,
            num_uniform_buffers=1,
        )

        # ======================================================
        # Sampler
        # ======================================================

        self._sampler = GPUSampler(
            self.device,
            min_filter=(
                sdl3.SDL_GPU_FILTER_NEAREST
            ),
            mag_filter=(
                sdl3.SDL_GPU_FILTER_NEAREST
            ),
            mipmap_mode=(
                sdl3.SDL_GPU_SAMPLERMIPMAPMODE_NEAREST
            ),
            address_mode_u=(
                sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
            ),
            address_mode_v=(
                sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
            ),
            address_mode_w=(
                sdl3.SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE
            ),
        )

        # ======================================================
        # Buffers
        # ======================================================

        self._vertex_buffer = (
            self._create_quad_buffer()
        )

        self._instance_buffer = GPUBuffer(
            self.device,
            self.max_glyphs
            * INSTANCE_STRIDE,
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            dynamic=True,
            frames_in_flight=(
                context.frames_in_flight
            ),
        )

        # ======================================================
        # Pipeline
        # ======================================================

        self._pipeline = (
            self._create_pipeline()
        )

        # ======================================================
        # CPU instance data
        # ======================================================

        self._instances = bytearray(
            self.max_glyphs
            * INSTANCE_STRIDE
        )

        self._glyph_count = 0

        self._clip_rects: list[
            tuple[
                float,
                float,
                float,
                float,
            ]
            | None
        ] = []

        # ======================================================
        # Text state
        # ======================================================

        self._text_color = (
            1.0,
            1.0,
            1.0,
            1.0,
        )

        self._destroyed = False

    # ==============================================================
    # Utility
    # ==============================================================

    @staticmethod
    def _error() -> str:
        error = sdl3.SDL_GetError()

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

    # ==============================================================
    # Quad
    # ==============================================================

    def _create_quad_buffer(
        self,
    ):
        """
        Creates a static quad.

        Vertex layout:

            float2 position
            float2 uv
        """

        vertices = struct.pack(
            "<24f",

            # Triangle 1
            -0.5,
            -0.5,
            0.0,
            0.0,

            0.5,
            -0.5,
            1.0,
            0.0,

            0.5,
            0.5,
            1.0,
            1.0,

            # Triangle 2
            -0.5,
            -0.5,
            0.0,
            0.0,

            0.5,
            0.5,
            1.0,
            1.0,

            -0.5,
            0.5,
            0.0,
            1.0,
        )

        return GPUBuffer(
            self.device,
            len(
                vertices
            ),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            initial_data=vertices,
            dynamic=False,
        )

    # ==============================================================
    # Pipeline
    # ==============================================================

    def _attribute(
        self,
        location: int,
        slot: int,
        fmt,
        offset: int,
    ):
        attribute = (
            sdl3.SDL_GPUVertexAttribute()
        )

        attribute.location = int(
            location
        )

        attribute.buffer_slot = int(
            slot
        )

        attribute.format = fmt

        attribute.offset = int(
            offset
        )

        return attribute

    def _create_pipeline(
        self,
    ):
        # ----------------------------------------------------------
        # Vertex buffer descriptions
        # ----------------------------------------------------------

        vertex_input = (
            sdl3.SDL_GPUVertexBufferDescription()
        )

        vertex_input.slot = 0

        vertex_input.pitch = 16

        vertex_input.input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )

        vertex_input.instance_step_rate = 0

        instance_input = (
            sdl3.SDL_GPUVertexBufferDescription()
        )

        instance_input.slot = 1

        instance_input.pitch = (
            INSTANCE_STRIDE
        )

        instance_input.input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_INSTANCE
        )

        instance_input.instance_step_rate = 0

        vertex_buffers = (
            sdl3.SDL_GPUVertexBufferDescription
            * 2
        )()

        vertex_buffers[0] = (
            vertex_input
        )

        vertex_buffers[1] = (
            instance_input
        )

        # ----------------------------------------------------------
        # Vertex attributes
        # ----------------------------------------------------------

        attributes = (
            sdl3.SDL_GPUVertexAttribute
            * 11
        )()

        # Static quad position
        attributes[0] = self._attribute(
            0,
            0,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2,
            0,
        )

        # Static quad UV
        attributes[1] = self._attribute(
            1,
            0,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2,
            8,
        )

        # Instance position
        attributes[2] = self._attribute(
            2,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2,
            0,
        )

        # Instance size
        attributes[3] = self._attribute(
            3,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2,
            8,
        )

        # Rotation
        attributes[4] = self._attribute(
            4,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT,
            16,
        )

        # Origin
        attributes[5] = self._attribute(
            5,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2,
            20,
        )

        # Alpha
        attributes[6] = self._attribute(
            6,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT,
            28,
        )

        # Flip X
        attributes[7] = self._attribute(
            7,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT,
            32,
        )

        # Flip Y
        attributes[8] = self._attribute(
            8,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT,
            36,
        )

        # Atlas UV
        attributes[9] = self._attribute(
            9,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2,
            40,
        )

        # Atlas UV size
        attributes[10] = self._attribute(
            10,
            1,
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2,
            48,
        )

        # ----------------------------------------------------------
        # Vertex input state
        # ----------------------------------------------------------

        vertex_input_state = (
            sdl3.SDL_GPUVertexInputState()
        )

        vertex_input_state.vertex_buffer_descriptions = (
            vertex_buffers
        )

        vertex_input_state.num_vertex_buffers = 2

        vertex_input_state.vertex_attributes = (
            attributes
        )

        vertex_input_state.num_vertex_attributes = 11

        # ----------------------------------------------------------
        # Pipeline info
        # ----------------------------------------------------------

        pipeline_info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        pipeline_info.vertex_shader = (
            self._vertex_shader.shader
        )

        pipeline_info.fragment_shader = (
            self._fragment_shader.shader
        )

        pipeline_info.vertex_input_state = (
            vertex_input_state
        )

        pipeline_info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        # ----------------------------------------------------------
        # Rasterizer
        # ----------------------------------------------------------

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

        rasterizer.enable_depth_clip = True

        pipeline_info.rasterizer_state = (
            rasterizer
        )

        # ----------------------------------------------------------
        # Multisampling
        # ----------------------------------------------------------

        multisample = (
            sdl3.SDL_GPUMultisampleState()
        )

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False

        pipeline_info.multisample_state = (
            multisample
        )

        # ----------------------------------------------------------
        # Depth / stencil
        # ----------------------------------------------------------

        depth_stencil = (
            sdl3.SDL_GPUDepthStencilState()
        )

        depth_stencil.enable_depth_test = False
        depth_stencil.enable_depth_write = False
        depth_stencil.enable_stencil_test = False

        pipeline_info.depth_stencil_state = (
            depth_stencil
        )

        # ----------------------------------------------------------
        # Color target
        # ----------------------------------------------------------

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = (
            self.context.swapchain_format
        )

        blend = (
            sdl3.SDL_GPUColorTargetBlendState()
        )

        blend.enable_blend = True

        blend.src_color_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_SRC_ALPHA
        )

        blend.dst_color_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA
        )

        blend.color_blend_op = (
            sdl3.SDL_GPU_BLENDOP_ADD
        )

        blend.src_alpha_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE
        )

        blend.dst_alpha_blendfactor = (
            sdl3.SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA
        )

        blend.alpha_blend_op = (
            sdl3.SDL_GPU_BLENDOP_ADD
        )

        blend.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        color_target.blend_state = (
            blend
        )

        color_targets = (
            sdl3.SDL_GPUColorTargetDescription
            * 1
        )()

        color_targets[0] = (
            color_target
        )

        pipeline_info.target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        pipeline_info.target_info.color_target_descriptions = (
            color_targets
        )

        pipeline_info.target_info.num_color_targets = 1

        # ----------------------------------------------------------
        # Create pipeline
        # ----------------------------------------------------------

        pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                pipeline_info,
            )
        )

        if not pipeline:
            raise RuntimeError(
                "SDL_CreateGPUGraphicsPipeline failed: "
                + self._error()
            )

        return pipeline

    # ==============================================================
    # Batch management
    # ==============================================================

    def clear(
        self,
    ) -> None:
        self._glyph_count = 0

        self._clip_rects.clear()

    @property
    def glyph_count(
        self,
    ) -> int:
        return self._glyph_count

    # ==============================================================
    # Color
    # ==============================================================

    def set_color(
        self,
        r: float,
        g: float,
        b: float,
        a: float = 1.0,
    ) -> None:
        self._text_color = (
            float(r),
            float(g),
            float(b),
            float(a),
        )

    @property
    def color(
        self,
    ):
        return self._text_color

    # ==============================================================
    # Text measurement
    # ==============================================================

    def measure(
        self,
        text: str,
        *,
        scale: float = 1.0,
    ) -> tuple[
        float,
        float,
    ]:
        """
        Measure the rendered size of a text string.

        Returns:
            (width, height)
        """

        if scale <= 0:
            raise ValueError(
                "scale must be greater than zero."
            )

        if not text:
            return (
                0.0,
                0.0,
            )

        current_width = 0.0
        max_width = 0.0
        line_count = 1

        for character in text:
            if character == "\n":
                max_width = max(
                    max_width,
                    current_width,
                )

                current_width = 0.0
                line_count += 1

                continue

            glyph = self.font.glyph(
                ord(
                    character
                )
            )

            current_width += (
                glyph.advance
                * scale
            )

        max_width = max(
            max_width,
            current_width,
        )

        height = (
            self.font.line_skip
            * line_count
            * scale
        )

        return (
            max_width,
            height,
        )

    # ==============================================================
    # Text generation
    # ==============================================================

    def draw(
        self,
        text: str,
        x: float,
        y: float,
        *,
        rotation: float = 0.0,
        alpha: float = 1.0,
        scale: float = 1.0,
        clip_rect: tuple[
            float,
            float,
            float,
            float,
        ] | None = None,
    ) -> int:
        """
        Add text to the current batch.

        x/y represent the text baseline.
        Returns the number of generated glyph instances.
        """

        if not text:
            return 0

        start_glyph_count = self._glyph_count

        if scale <= 0:
            raise ValueError(
                "scale must be greater than zero."
            )

        cursor_x = float(
            x
        )

        baseline_y = float(
            y
        )

        line_start_x = cursor_x

        for character in text:
            # --------------------------------------------------
            # New line
            # --------------------------------------------------

            if character == "\n":
                cursor_x = (
                    line_start_x
                )

                baseline_y += (
                    self.font.line_skip
                    * scale
                )

                continue

            codepoint = ord(
                character
            )

            glyph = self.font.glyph(
                codepoint
            )

            atlas_glyph = (
                self.atlas.get_glyph(
                    codepoint
                )
            )

            if atlas_glyph is None:
                cursor_x += (
                    glyph.advance
                    * scale
                )

                continue

            if (
                self._glyph_count
                >= self.max_glyphs
            ):
                raise RuntimeError(
                    "GPUTextRenderer instance buffer "
                    "is full. Maximum glyphs: "
                    f"{self.max_glyphs}"
                )

            # --------------------------------------------------
            # Glyph dimensions
            # --------------------------------------------------

            glyph_width = (
                atlas_glyph.width
                * scale
            )

            glyph_height = (
                atlas_glyph.height
                * scale
            )

            # --------------------------------------------------
            # Glyph position
            # --------------------------------------------------

            glyph_x = (
                cursor_x
                + glyph.bearing_x
                * scale
            )

            glyph_y = (
                baseline_y
                - glyph.bearing_y
                * scale
            )

            instance_x = (
                glyph_x
                + glyph_width
                * 0.5
            )

            instance_y = (
                glyph_y
                + glyph_height
                * 0.5
            )

            # --------------------------------------------------
            # Instance
            # --------------------------------------------------

            offset = (
                self._glyph_count
                * INSTANCE_STRIDE
            )

            struct.pack_into(
                "<14f",
                self._instances,
                offset,

                # position
                instance_x,
                instance_y,

                # size
                glyph_width,
                glyph_height,

                # rotation
                float(
                    rotation
                ),

                # origin
                0.5,
                0.5,

                # alpha
                float(
                    alpha
                ),

                # flip x/y
                0.0,
                0.0,

                # atlas UV
                atlas_glyph.u,
                atlas_glyph.v,

                # atlas UV size
                atlas_glyph.u_size,
                atlas_glyph.v_size,
            )

            if clip_rect is None:
                self._clip_rects.append(
                    None
                )

            else:
                (
                    clip_x,
                    clip_y,
                    clip_width,
                    clip_height,
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
                                clip_width
                            ),
                            0.0,
                        ),
                        max(
                            float(
                                clip_height
                            ),
                            0.0,
                        ),
                    )
                )

            self._glyph_count += 1

            # --------------------------------------------------
            # Advance cursor
            # --------------------------------------------------

            cursor_x += (
                glyph.advance
                * scale
            )

        return (
            self._glyph_count
            - start_glyph_count
        )

    # ==============================================================
    # GPU upload
    # ==============================================================

    def render_into(
        self,
        command_buffer,
    ) -> None:
        """
        Upload current instance data to the GPU.
        """

        if self._glyph_count <= 0:
            return

        data_size = (
            self._glyph_count
            * INSTANCE_STRIDE
        )

        self._instance_buffer.upload_into(
            command_buffer,
            memoryview(
                self._instances
            )[:data_size],
        )

    # ==============================================================
    # Scissor
    # ==============================================================

    def _make_scissor_rect(
        self,
        clip_rect: tuple[
            float,
            float,
            float,
            float,
        ] | None,
    ) -> sdl3.SDL_Rect:
        """
        Convert a Nexora screen-space clip rectangle to SDL_Rect.

        Nexora uses the screen center as (0, 0).
        SDL scissor rectangles use the framebuffer top-left
        as (0, 0).
        """

        viewport_width = max(
            int(
                self.context.swapchain_width
            ),
            0,
        )

        viewport_height = max(
            int(
                self.context.swapchain_height
            ),
            0,
        )

        if clip_rect is None:
            left = 0
            top = 0

            right = (
                viewport_width
            )

            bottom = (
                viewport_height
            )

        else:
            (
                x,
                y,
                width,
                height,
            ) = clip_rect

            half_width = (
                viewport_width
                * 0.5
            )

            half_height = (
                viewport_height
                * 0.5
            )

            left = math.floor(
                x
                + half_width
            )

            top = math.floor(
                y
                + half_height
            )

            right = math.ceil(
                x
                + width
                + half_width
            )

            bottom = math.ceil(
                y
                + height
                + half_height
            )

            left = max(
                0,
                min(
                    left,
                    viewport_width,
                ),
            )

            top = max(
                0,
                min(
                    top,
                    viewport_height,
                ),
            )

            right = max(
                left,
                min(
                    right,
                    viewport_width,
                ),
            )

            bottom = max(
                top,
                min(
                    bottom,
                    viewport_height,
                ),
            )

        rect = (
            sdl3.SDL_Rect()
        )

        rect.x = int(
            left
        )

        rect.y = int(
            top
        )

        rect.w = int(
            right
            - left
        )

        rect.h = int(
            bottom
            - top
        )

        return rect

    # ==============================================================
    # Draw
    # ==============================================================

    def draw_into(
        self,
        render_pass,
    ) -> None:
        """
        Draw the current text batch.

        Must be called inside an active GPU render pass.
        """

        if self._glyph_count <= 0:
            return

        command_buffer = (
            self.context.command_buffer
        )

        if command_buffer is None:
            raise RuntimeError(
                "No active GPU command buffer."
            )

        # ----------------------------------------------------------
        # Camera uniform
        # ----------------------------------------------------------

        camera_data = struct.pack(
            "<8f",

            # camera position
            0.0,
            0.0,

            # viewport
            float(
                self.context.swapchain_width
            ),
            float(
                self.context.swapchain_height
            ),

            # zoom
            1.0,

            # shake
            0.0,
            0.0,

            # padding
            0.0,
        )

        sdl3.SDL_PushGPUVertexUniformData(
            command_buffer,
            0,
            camera_data,
            len(
                camera_data
            ),
        )

        # ----------------------------------------------------------
        # Text color uniform
        # ----------------------------------------------------------

        color_data = struct.pack(
            "<4f",
            *self._text_color,
        )

        sdl3.SDL_PushGPUFragmentUniformData(
            command_buffer,
            0,
            color_data,
            len(
                color_data
            ),
        )

        # ----------------------------------------------------------
        # Pipeline
        # ----------------------------------------------------------

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self._pipeline,
        )

        # ----------------------------------------------------------
        # Vertex buffers
        # ----------------------------------------------------------

        vertex_bindings = (
            sdl3.SDL_GPUBufferBinding
            * 2
        )()

        vertex_bindings[0].buffer = (
            self._vertex_buffer
            .current_buffer
        )

        vertex_bindings[0].offset = 0

        vertex_bindings[1].buffer = (
            self._instance_buffer
            .current_buffer
        )

        vertex_bindings[1].offset = 0

        sdl3.SDL_BindGPUVertexBuffers(
            render_pass,
            0,
            vertex_bindings,
            2,
        )

        # ----------------------------------------------------------
        # Font atlas
        # ----------------------------------------------------------

        texture_binding = (
            sdl3.SDL_GPUTextureSamplerBinding()
        )

        texture_binding.texture = (
            self.atlas
            .texture
            .texture
        )

        texture_binding.sampler = (
            self._sampler.sampler
        )

        texture_bindings = (
            sdl3.SDL_GPUTextureSamplerBinding
            * 1
        )()

        texture_bindings[0] = (
            texture_binding
        )

        sdl3.SDL_BindGPUFragmentSamplers(
            render_pass,
            0,
            texture_bindings,
            1,
        )

        # ----------------------------------------------------------
        # Draw consecutive clip groups
        # ----------------------------------------------------------

        run_start = 0

        while (
            run_start
            < self._glyph_count
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
                < self._glyph_count
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

                sdl3.SDL_DrawGPUPrimitives(
                    render_pass,
                    6,
                    run_end
                    - run_start,
                    0,
                    run_start,
                )

            run_start = (
                run_end
            )

        # ----------------------------------------------------------
        # Restore unclipped state
        # ----------------------------------------------------------

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

    # ==============================================================
    # Draw range
    # ==============================================================

    def draw_range(
        self,
        render_pass,
        start: int,
        count: int,
    ) -> int:
        if count <= 0:
            return 0

        start = int(start)
        count = int(count)

        if start < 0:
            raise ValueError(
                "start must be greater than or equal to zero"
            )

        end = start + count

        if end > self._glyph_count:
            raise ValueError(
                "Text draw range exceeds current batch "
                f"({end} > {self._glyph_count})"
            )

        command_buffer = self.context.command_buffer

        if command_buffer is None:
            raise RuntimeError(
                "No active GPU command buffer."
            )

        camera_data = struct.pack(
            "<8f",
            0.0,
            0.0,
            float(self.context.swapchain_width),
            float(self.context.swapchain_height),
            1.0,
            0.0,
            0.0,
            0.0,
        )

        sdl3.SDL_PushGPUVertexUniformData(
            command_buffer,
            0,
            camera_data,
            len(camera_data),
        )

        color_data = struct.pack(
            "<4f",
            *self._text_color,
        )

        sdl3.SDL_PushGPUFragmentUniformData(
            command_buffer,
            0,
            color_data,
            len(color_data),
        )

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self._pipeline,
        )

        vertex_bindings = (
            sdl3.SDL_GPUBufferBinding * 2
        )()

        vertex_bindings[0].buffer = (
            self._vertex_buffer.current_buffer
        )
        vertex_bindings[0].offset = 0

        vertex_bindings[1].buffer = (
            self._instance_buffer.current_buffer
        )
        vertex_bindings[1].offset = 0

        sdl3.SDL_BindGPUVertexBuffers(
            render_pass,
            0,
            vertex_bindings,
            2,
        )

        texture_binding = (
            sdl3.SDL_GPUTextureSamplerBinding()
        )
        texture_binding.texture = self.atlas.texture.texture
        texture_binding.sampler = self._sampler.sampler

        texture_bindings = (
            sdl3.SDL_GPUTextureSamplerBinding * 1
        )()
        texture_bindings[0] = texture_binding

        sdl3.SDL_BindGPUFragmentSamplers(
            render_pass,
            0,
            texture_bindings,
            1,
        )

        drawn = 0
        run_start = start

        while run_start < end:
            clip_rect = self._clip_rects[run_start]
            run_end = run_start + 1

            while (
                run_end < end
                and self._clip_rects[run_end] == clip_rect
            ):
                run_end += 1

            scissor = self._make_scissor_rect(clip_rect)

            if scissor.w > 0 and scissor.h > 0:
                sdl3.SDL_SetGPUScissor(
                    render_pass,
                    ctypes.byref(scissor),
                )

                run_count = run_end - run_start

                sdl3.SDL_DrawGPUPrimitives(
                    render_pass,
                    6,
                    run_count,
                    0,
                    run_start,
                )

                drawn += run_count

            run_start = run_end

        full_scissor = self._make_scissor_rect(None)

        sdl3.SDL_SetGPUScissor(
            render_pass,
            ctypes.byref(full_scissor),
        )

        return drawn

    # ==============================================================
    # Convenience frame rendering
    # ==============================================================

    def end(
        self,
        *,
        clear_color=(
            0.05,
            0.05,
            0.05,
            1.0,
        ),
    ) -> None:
        """
        Convenience method for rendering a complete frame.

        For integration with other renderers, use:

            renderer.render_into(command_buffer)
            renderer.draw_into(render_pass)
        """

        if not self.context.begin_frame():
            self.clear()

            return

        try:
            command_buffer = (
                self.context.command_buffer
            )

            self.render_into(
                command_buffer
            )

            render_pass = (
                self.context.begin_render_pass(
                    clear_color
                )
            )

            try:
                self.draw_into(
                    render_pass
                )

            finally:
                self.context.end_render_pass(
                    render_pass
                )

            self.context.end_frame()

        except Exception:
            self.context.cancel_frame()

            raise

        finally:
            self.clear()

    # ==============================================================
    # Atlas access
    # ==============================================================

    @property
    def atlas_texture(
        self,
    ):
        if self.atlas is None:
            return None

        return self.atlas.texture

    # ==============================================================
    # Cleanup
    # ==============================================================

    def destroy(
        self,
    ) -> None:
        if self._destroyed:
            return

        self.context.wait_idle()

        # ----------------------------------------------------------
        # Pipeline
        # ----------------------------------------------------------

        if self._pipeline is not None:
            sdl3.SDL_ReleaseGPUGraphicsPipeline(
                self.device,
                self._pipeline,
            )

            self._pipeline = None

        # ----------------------------------------------------------
        # Instance buffer
        # ----------------------------------------------------------

        if self._instance_buffer is not None:
            self._instance_buffer.destroy()

            self._instance_buffer = None

        # ----------------------------------------------------------
        # Quad buffer
        # ----------------------------------------------------------

        if self._vertex_buffer is not None:
            self._vertex_buffer.destroy()

            self._vertex_buffer = None

        # ----------------------------------------------------------
        # Sampler
        # ----------------------------------------------------------

        if self._sampler is not None:
            self._sampler.destroy()

            self._sampler = None

        # ----------------------------------------------------------
        # Shaders
        # ----------------------------------------------------------

        if self._vertex_shader is not None:
            self._vertex_shader.destroy()

            self._vertex_shader = None

        if self._fragment_shader is not None:
            self._fragment_shader.destroy()

            self._fragment_shader = None

        # ----------------------------------------------------------
        # Atlas
        # ----------------------------------------------------------

        if self.atlas is not None:
            self.atlas.destroy()

            self.atlas = None

        self._clip_rects.clear()

        self._destroyed = True

    # ==============================================================
    # Context manager
    # ==============================================================

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.destroy()