from __future__ import annotations

import ctypes

import sdl3


class GPUPipeline:
    """
    Graphics pipeline wrapper for SDL_GPU.
    """

    def __init__(
        self,
        device,
        *,
        vertex_shader,
        fragment_shader,
        vertex_buffer_descriptions,
        vertex_attributes,
        primitive_type=sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST,
        target_format,
    ):
        self.device = device
        self.pipeline = None

        # SDL keeps pointers to these arrays.
        # Keep them alive for the lifetime of the pipeline.
        self._vertex_buffer_descriptions = (
            vertex_buffer_descriptions
        )

        self._vertex_attributes = vertex_attributes

        self._color_targets = None

        self._create(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
            primitive_type=primitive_type,
            target_format=target_format,
        )

    def _create(
        self,
        *,
        vertex_shader,
        fragment_shader,
        primitive_type,
        target_format,
    ):
        # ==========================================================
        # VERTEX INPUT
        # ==========================================================

        vertex_input = sdl3.SDL_GPUVertexInputState()

        vertex_input.vertex_buffer_descriptions = (
            self._vertex_buffer_descriptions
        )

        vertex_input.num_vertex_buffers = len(
            self._vertex_buffer_descriptions
        )

        vertex_input.vertex_attributes = (
            self._vertex_attributes
        )

        vertex_input.num_vertex_attributes = len(
            self._vertex_attributes
        )

        # ==========================================================
        # RASTERIZER
        #
        # Keep this minimal. ctypes structures are zero initialized,
        # and SDL's defaults are sufficient for this test.
        # ==========================================================

        rasterizer = sdl3.SDL_GPURasterizerState()

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

        # ==========================================================
        # MULTISAMPLING
        # ==========================================================

        multisample = sdl3.SDL_GPUMultisampleState()

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        # Explicitly disable optional features.
        multisample.enable_mask = False
        multisample.enable_alpha_to_coverage = False

        # ==========================================================
        # DEPTH / STENCIL
        # ==========================================================

        depth = sdl3.SDL_GPUDepthStencilState()

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        # ==========================================================
        # COLOR TARGET
        # ==========================================================

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = target_format

        # No blending.
        color_target.blend_state.enable_blend = False

        # Enable writing all RGBA channels.
        color_target.blend_state.enable_color_write_mask = True

        color_target.blend_state.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        self._color_targets = (
            sdl3.SDL_GPUColorTargetDescription * 1
        )()

        self._color_targets[0] = color_target

        # ==========================================================
        # TARGET INFO
        # ==========================================================

        target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        target_info.color_target_descriptions = (
            self._color_targets
        )

        target_info.num_color_targets = 1

        # IMPORTANT:
        #
        # There is no depth target.
        #
        # SDL_GPU_TEXTUREFORMAT_INVALID is the correct value here.
        #
        target_info.depth_stencil_format = (
            sdl3.SDL_GPU_TEXTUREFORMAT_INVALID
        )

        target_info.has_depth_stencil_target = False

        # ==========================================================
        # PIPELINE INFO
        # ==========================================================

        info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        info.vertex_shader = vertex_shader
        info.fragment_shader = fragment_shader

        info.vertex_input_state = vertex_input

        info.primitive_type = primitive_type

        info.rasterizer_state = rasterizer

        info.multisample_state = multisample

        info.depth_stencil_state = depth

        info.target_info = target_info

        info.props = 0

        # ==========================================================
        # CREATE
        # ==========================================================

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.device,
                ctypes.byref(info),
            )
        )

        if not self.pipeline:
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                "SDL_CreateGPUGraphicsPipeline failed: "
                f"{error}"
            )

    def bind(self, render_pass) -> None:
        if not self.pipeline:
            raise RuntimeError(
                "GPU pipeline is not initialized"
            )

        sdl3.SDL_BindGPUGraphicsPipeline(
            render_pass,
            self.pipeline,
        )

    def destroy(self) -> None:
        if self.pipeline:
            sdl3.SDL_ReleaseGPUGraphicsPipeline(
                self.device,
                self.pipeline,
            )

            self.pipeline = None

        self._color_targets = None
        self._vertex_attributes = None
        self._vertex_buffer_descriptions = None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()