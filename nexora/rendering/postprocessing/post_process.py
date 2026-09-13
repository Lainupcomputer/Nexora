from __future__ import annotations

import struct
import time
from pathlib import Path

import sdl3

from nexora.rendering.gpu.pipeline import GPUPipeline
from nexora.rendering.gpu.sampler import GPUSampler
from nexora.rendering.gpu.shader import GPUShader
from nexora.rendering.gpu.texture import GPUTexture
from nexora.rendering.postprocessing.effects import (
    PostProcessEffects,
)

class PostProcess:
    """
    Nexora fullscreen post-processing pass.

    Post-processing is disabled by default.

    GPU resources are lazily created when enable() is called.

    Built-in effects:

        - grayscale
        - vignette
        - brightness
        - contrast
        - saturation
        - tint / color grading
        - chromatic aberration
        - film grain
        - scanlines
        - pixelation
        - distortion
        - low-health damage pulse
    """

    def __init__(
        self,
        context,
    ) -> None:
        self.context = context

        self.device = (
            context.device
        )

        # ======================================================
        # State
        # ======================================================

        self.enabled: bool = False

        self.initialized: bool = False

        self._start_time = (
            time.perf_counter()
        )

        # ======================================================
        # Basic color effects
        # ======================================================

        self.grayscale: float = 0.0

        self.vignette: float = 0.0

        self.brightness: float = 1.0

        self.contrast: float = 1.0

        self.saturation: float = 1.0

        # ======================================================
        # Color grading
        # ======================================================

        self.tint: tuple[
            float,
            float,
            float,
        ] = (
            1.0,
            1.0,
            1.0,
        )

        # ======================================================
        # Chromatic aberration
        #
        # Specified approximately in screen pixels.
        # ======================================================

        self.chromatic_aberration: float = 0.0

        # ======================================================
        # Film grain
        # ======================================================

        self.film_grain: float = 0.0

        # ======================================================
        # Scanlines
        # ======================================================

        self.scanlines: float = 0.0

        self.scanline_frequency: float = 1.0

        # ======================================================
        # Pixelation
        #
        # 1.0 = disabled
        # 2+ = pixel block size
        # ======================================================

        self.pixel_size: float = 1.0

        # ======================================================
        # Distortion
        # ======================================================

        self.distortion: float = 0.0

        self.distortion_speed: float = 1.0

        # ======================================================
        # Damage / low health
        #
        # health:
        #   1.0 = full health
        #   0.0 = dead / critical
        #
        # damage_pulse:
        #   overall effect strength
        # ======================================================

        self.health: float = 1.0

        self.damage_pulse: float = 0.0

        # ======================================================
        # Render target
        # ======================================================

        self.render_target: (
            GPUTexture | None
        ) = None

        self._width: int = 0
        self._height: int = 0

        # ======================================================
        # GPU resources
        # ======================================================

        self.vertex_shader = None

        self.fragment_shader = None

        self.pipeline = None

        self.sampler = None
        self.effects = PostProcessEffects(
            self
        )

    # ==========================================================
    # Utility
    # ==========================================================

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(
                maximum,
                float(value),
            ),
        )

    # ==========================================================
    # Enable / disable
    # ==========================================================

    def enable(
        self,
    ) -> None:
        if not self.initialized:
            self._create_resources()

            self.initialized = True

        self.enabled = True

    def disable(
        self,
    ) -> None:
        self.enabled = False

    # ==========================================================
    # Health
    # ==========================================================

    def set_health(
        self,
        health: float,
    ) -> None:
        """
        Set normalized player health.

        0.0 = empty
        1.0 = full
        """

        self.health = self._clamp(
            health,
            0.0,
            1.0,
        )

    # ==========================================================
    # Pixelation
    # ==========================================================

    def set_pixel_size(
        self,
        size: float,
    ) -> None:
        self.pixel_size = max(
            1.0,
            float(size),
        )

    # ==========================================================
    # Resources
    # ==========================================================

    def _create_resources(
        self,
    ) -> None:
        if self.initialized:
            return

        shader_dir = (
            Path(__file__)
            .resolve()
            .parent
            .parent
            / "shaders"
            / "bin"
        )

        try:
            self.vertex_shader = GPUShader(
                self.device,
                shader_dir
                / "post_process.vert.spv",
                sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
                sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
                entrypoint="main",
            )

            self.fragment_shader = GPUShader(
                self.device,
                shader_dir
                / "post_process.frag.spv",
                sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
                sdl3.SDL_GPU_SHADERFORMAT_SPIRV,
                entrypoint="main",
                num_samplers=1,
                num_uniform_buffers=1,
            )

            self.sampler = GPUSampler(
                self.device,
                min_filter=(
                    sdl3.SDL_GPU_FILTER_LINEAR
                ),
                mag_filter=(
                    sdl3.SDL_GPU_FILTER_LINEAR
                ),
            )

            self._create_pipeline()

        except Exception:
            self._destroy_resources()

            raise

    # ==========================================================
    # Pipeline
    # ==========================================================

    def _create_pipeline(
        self,
    ) -> None:
        if (
            self.vertex_shader is None
            or self.fragment_shader is None
        ):
            raise RuntimeError(
                "Post-processing shaders are not initialized"
            )

        vertex_buffers = (
            sdl3.SDL_GPUVertexBufferDescription
            * 0
        )()

        attributes = (
            sdl3.SDL_GPUVertexAttribute
            * 0
        )()

        self.pipeline = GPUPipeline(
            self.device,
            vertex_shader=(
                self.vertex_shader.shader
            ),
            fragment_shader=(
                self.fragment_shader.shader
            ),
            vertex_buffer_descriptions=(
                vertex_buffers
            ),
            vertex_attributes=(
                attributes
            ),
            primitive_type=(
                sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
            ),
            target_format=(
                self.context.swapchain_format
            ),
        )

    # ==========================================================
    # Render target
    # ==========================================================

    def ensure_target(
        self,
        width: int,
        height: int,
    ) -> None:
        if not self.initialized:
            self._create_resources()

            self.initialized = True

        width = int(
            width
        )

        height = int(
            height
        )

        if (
            width <= 0
            or height <= 0
        ):
            return

        if (
            self.render_target is not None
            and self._width == width
            and self._height == height
        ):
            return

        if self.render_target is not None:
            self.render_target.destroy()

            self.render_target = None

        self.render_target = GPUTexture(
            self.device,
            width,
            height,
            format=(
                self.context.swapchain_format
            ),
            usage=(
                sdl3.SDL_GPU_TEXTUREUSAGE_SAMPLER
                | sdl3.SDL_GPU_TEXTUREUSAGE_COLOR_TARGET
            ),
        )

        self._width = width
        self._height = height

    # ==========================================================
    # Uniforms
    # ==========================================================

    def _push_uniforms(
        self,
        command_buffer,
    ) -> None:
        elapsed_time = (
            time.perf_counter()
            - self._start_time
        )

        data = struct.pack(
            "<20f",

            # --------------------------------------------------
            # color_settings
            # --------------------------------------------------

            float(
                self.grayscale
            ),

            float(
                self.vignette
            ),

            float(
                self.brightness
            ),

            float(
                self.contrast
            ),

            # --------------------------------------------------
            # effect_settings
            # --------------------------------------------------

            float(
                self.saturation
            ),

            float(
                self.chromatic_aberration
            ),

            float(
                self.film_grain
            ),

            float(
                self.scanlines
            ),

            # --------------------------------------------------
            # dynamic_settings
            # --------------------------------------------------

            float(
                self.pixel_size
            ),

            float(
                self.distortion
            ),

            float(
                elapsed_time
            ),

            float(
                self.health
            ),

            # --------------------------------------------------
            # screen_settings
            # --------------------------------------------------

            float(
                self.damage_pulse
            ),

            float(
                self.scanline_frequency
            ),

            float(
                self._width
            ),

            float(
                self._height
            ),

            # --------------------------------------------------
            # tint_settings
            # --------------------------------------------------

            float(
                self.tint[0]
            ),

            float(
                self.tint[1]
            ),

            float(
                self.tint[2]
            ),

            float(
                self.distortion_speed
            ),
        )

        sdl3.SDL_PushGPUFragmentUniformData(
            command_buffer,
            0,
            data,
            len(
                data
            ),
        )

    # ==========================================================
    # Draw
    # ==========================================================

    def draw(
        self,
        render_pass,
        command_buffer,
    ) -> None:
        if not self.enabled:
            return

        if not self.initialized:
            return

        if self.render_target is None:
            return

        if self.pipeline is None:
            return

        if self.sampler is None:
            return

        self.pipeline.bind(
            render_pass
        )

        self._push_uniforms(
            command_buffer
        )

        binding = (
            sdl3.SDL_GPUTextureSamplerBinding()
        )

        binding.texture = (
            self.render_target.texture
        )

        binding.sampler = (
            self.sampler.sampler
        )

        bindings = (
            sdl3.SDL_GPUTextureSamplerBinding
            * 1
        )()

        bindings[0] = binding

        sdl3.SDL_BindGPUFragmentSamplers(
            render_pass,
            0,
            bindings,
            1,
        )

        sdl3.SDL_DrawGPUPrimitives(
            render_pass,
            3,
            1,
            0,
            0,
        )

    # ==========================================================
    # Reset
    # ==========================================================

    def reset(
        self,
    ) -> None:
        """
        Reset all post-processing effects to neutral values.
        """

        self.grayscale = 0.0

        self.vignette = 0.0

        self.brightness = 1.0

        self.contrast = 1.0

        self.saturation = 1.0

        self.tint = (
            1.0,
            1.0,
            1.0,
        )

        self.chromatic_aberration = 0.0

        self.film_grain = 0.0

        self.scanlines = 0.0

        self.scanline_frequency = 1.0

        self.pixel_size = 1.0

        self.distortion = 0.0

        self.distortion_speed = 1.0

        self.health = 1.0

        self.damage_pulse = 0.0

    # ==========================================================
    # Resource cleanup
    # ==========================================================

    def _destroy_resources(
        self,
    ) -> None:
        if self.render_target is not None:
            self.render_target.destroy()

            self.render_target = None

        if self.pipeline is not None:
            self.pipeline.destroy()

            self.pipeline = None

        if self.sampler is not None:
            self.sampler.destroy()

            self.sampler = None

        if self.vertex_shader is not None:
            self.vertex_shader.destroy()

            self.vertex_shader = None

        if self.fragment_shader is not None:
            self.fragment_shader.destroy()

            self.fragment_shader = None

        self._width = 0
        self._height = 0

    # ==========================================================
    # Destroy
    # ==========================================================

    def destroy(
        self,
    ) -> None:
        self.enabled = False

        self._destroy_resources()

        self.initialized = False