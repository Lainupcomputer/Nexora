from __future__ import annotations

import ctypes
import os
from pathlib import Path

# Vulkan erzwingen, bevor SDL_GPU initialisiert wird.
os.environ["SDL_GPU_DRIVER"] = "vulkan"

import sdl3

from nexora.rendering.gpu.context import GPUContext


ROOT = Path(__file__).resolve().parents[1]

VERTEX_SHADER = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
    / "bufferless.vert.spv"
)

FRAGMENT_SHADER = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
    / "bufferless.frag.spv"
)


class VulkanBufferlessTest:

    def __init__(self):

        self.context: GPUContext | None = None

        self.vertex_shader = None
        self.fragment_shader = None
        self.pipeline = None

        self.running = True

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def check(value, message):

        if not value:

            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"{message}: {error}"
            )

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def initialize(self):

        print()
        print("=" * 60)
        print("NEXORA SDL_GPU VULKAN BUFFERLESS PIPELINE TEST")
        print("=" * 60)
        print()

        print("GPU backend:", os.environ.get("SDL_GPU_DRIVER"))
        print("Vertex shader:")
        print(f"  {VERTEX_SHADER}")
        print("Fragment shader:")
        print(f"  {FRAGMENT_SHADER}")
        print()

        if not VERTEX_SHADER.exists():
            raise FileNotFoundError(
                f"Vertex shader not found:\n{VERTEX_SHADER}"
            )

        if not FRAGMENT_SHADER.exists():
            raise FileNotFoundError(
                f"Fragment shader not found:\n{FRAGMENT_SHADER}"
            )

        # -----------------------------------------------------
        # Context
        # -----------------------------------------------------

        print("[1/4] Creating Vulkan GPU context...")

        self.context = GPUContext(
            800,
            600,
            "Nexora Vulkan Bufferless Test",
            debug=True,
            frames_in_flight=2,
        )

        print("      Driver:", self.context.driver)
        print(
            "      Swapchain format:",
            self.context.swapchain_format,
        )
        print()

        # -----------------------------------------------------
        # Load shaders
        # -----------------------------------------------------

        print("[2/4] Loading SPIR-V shaders...")

        vertex_data = VERTEX_SHADER.read_bytes()
        fragment_data = FRAGMENT_SHADER.read_bytes()

        print(
            "      Vertex SPIR-V:",
            len(vertex_data),
            "bytes",
        )

        print(
            "      Fragment SPIR-V:",
            len(fragment_data),
            "bytes",
        )

        # Keep ctypes buffers alive as long as the shader exists.
        self._vertex_data_buffer = (
            ctypes.c_ubyte * len(vertex_data)
        ).from_buffer_copy(vertex_data)

        self._fragment_data_buffer = (
            ctypes.c_ubyte * len(fragment_data)
        ).from_buffer_copy(fragment_data)

        # -----------------------------------------------------
        # Vertex shader
        # -----------------------------------------------------

        vertex_info = sdl3.SDL_GPUShaderCreateInfo()

        vertex_info.code_size = len(vertex_data)

        vertex_info.code = ctypes.cast(
            self._vertex_data_buffer,
            ctypes.POINTER(ctypes.c_ubyte),
        )

        vertex_info.entrypoint = b"main"

        vertex_info.format = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
        )

        vertex_info.stage = (
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX
        )

        vertex_info.num_samplers = 0
        vertex_info.num_storage_textures = 0
        vertex_info.num_storage_buffers = 0
        vertex_info.num_uniform_buffers = 0
        vertex_info.props = 0

        self.vertex_shader = (
            sdl3.SDL_CreateGPUShader(
                self.context.device,
                ctypes.byref(vertex_info),
            )
        )

        self.check(
            self.vertex_shader,
            "SDL_CreateGPUShader vertex failed",
        )

        print("      Vertex shader OK")

        # -----------------------------------------------------
        # Fragment shader
        # -----------------------------------------------------

        fragment_info = sdl3.SDL_GPUShaderCreateInfo()

        fragment_info.code_size = len(fragment_data)

        fragment_info.code = ctypes.cast(
            self._fragment_data_buffer,
            ctypes.POINTER(ctypes.c_ubyte),
        )

        fragment_info.entrypoint = b"main"

        fragment_info.format = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
        )

        fragment_info.stage = (
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT
        )

        fragment_info.num_samplers = 0
        fragment_info.num_storage_textures = 0
        fragment_info.num_storage_buffers = 0
        fragment_info.num_uniform_buffers = 0
        fragment_info.props = 0

        self.fragment_shader = (
            sdl3.SDL_CreateGPUShader(
                self.context.device,
                ctypes.byref(fragment_info),
            )
        )

        self.check(
            self.fragment_shader,
            "SDL_CreateGPUShader fragment failed",
        )

        print("      Fragment shader OK")
        print()

        # -----------------------------------------------------
        # Pipeline
        # -----------------------------------------------------

        print("[3/4] Creating bufferless graphics pipeline...")

        # No vertex buffers.
        vertex_input = sdl3.SDL_GPUVertexInputState()

        vertex_input.vertex_buffer_descriptions = None
        vertex_input.num_vertex_buffers = 0

        vertex_input.vertex_attributes = None
        vertex_input.num_vertex_attributes = 0

        # -----------------------------------------------------
        # Rasterizer
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Multisampling
        # -----------------------------------------------------

        multisample = sdl3.SDL_GPUMultisampleState()

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False
        multisample.enable_alpha_to_coverage = False

        # -----------------------------------------------------
        # Depth / stencil
        # -----------------------------------------------------

        depth = sdl3.SDL_GPUDepthStencilState()

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        # -----------------------------------------------------
        # Color target
        # -----------------------------------------------------

        color_target = (
            sdl3.SDL_GPUColorTargetDescription()
        )

        color_target.format = (
            self.context.swapchain_format
        )

        color_target.blend_state.enable_blend = False

        color_target.blend_state.enable_color_write_mask = True

        color_target.blend_state.color_write_mask = (
            sdl3.SDL_GPU_COLORCOMPONENT_R
            | sdl3.SDL_GPU_COLORCOMPONENT_G
            | sdl3.SDL_GPU_COLORCOMPONENT_B
            | sdl3.SDL_GPU_COLORCOMPONENT_A
        )

        # IMPORTANT:
        # ctypes needs an actual array instance,
        # not the array type itself.
        color_targets = (
            sdl3.SDL_GPUColorTargetDescription * 1
        )()

        color_targets[0] = color_target

        # -----------------------------------------------------
        # Target info
        # -----------------------------------------------------

        target_info = (
            sdl3.SDL_GPUGraphicsPipelineTargetInfo()
        )

        target_info.color_target_descriptions = (
            color_targets
        )

        target_info.num_color_targets = 1

        target_info.depth_stencil_format = (
            sdl3.SDL_GPU_TEXTUREFORMAT_INVALID
        )

        target_info.has_depth_stencil_target = False

        # -----------------------------------------------------
        # Pipeline create info
        # -----------------------------------------------------

        pipeline_info = (
            sdl3.SDL_GPUGraphicsPipelineCreateInfo()
        )

        pipeline_info.vertex_shader = (
            self.vertex_shader
        )

        pipeline_info.fragment_shader = (
            self.fragment_shader
        )

        pipeline_info.vertex_input_state = (
            vertex_input
        )

        pipeline_info.primitive_type = (
            sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
        )

        pipeline_info.rasterizer_state = (
            rasterizer
        )

        pipeline_info.multisample_state = (
            multisample
        )

        pipeline_info.depth_stencil_state = (
            depth
        )

        pipeline_info.target_info = (
            target_info
        )

        pipeline_info.props = 0

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.context.device,
                ctypes.byref(pipeline_info),
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

        print("      BUFFERLESS PIPELINE CREATED!")
        print()

        # -----------------------------------------------------
        # Render
        # -----------------------------------------------------

        print("[4/4] Starting rendering...")
        print()
        print("=" * 60)
        print("VULKAN PIPELINE CREATED SUCCESSFULLY")
        print("=" * 60)
        print()
        print("Rendering bufferless triangle.")
        print("Close the window to exit.")
        print()

    # ---------------------------------------------------------
    # Events
    # ---------------------------------------------------------

    def poll_events(self):

        event = sdl3.SDL_Event()

        while sdl3.SDL_PollEvent(
            ctypes.byref(event)
        ):

            event_type = event.type

            if event_type == sdl3.SDL_EVENT_QUIT:

                self.running = False

    # ---------------------------------------------------------
    # Render
    # ---------------------------------------------------------

    def render(self):

        if not self.context.begin_frame():
            return

        render_pass = None

        try:

            render_pass = (
                self.context.begin_render_pass(
                    (
                        0.05,
                        0.05,
                        0.08,
                        1.0,
                    )
                )
            )

            sdl3.SDL_BindGPUGraphicsPipeline(
                render_pass,
                self.pipeline,
            )

            # Bufferless triangle.
            #
            # Vertex shader uses SV_VertexID,
            # therefore no vertex buffer is required.
            sdl3.SDL_DrawGPUPrimitives(
                render_pass,
                3,
                1,
                0,
                0,
            )

            self.context.end_render_pass(
                render_pass
            )

            render_pass = None

            self.context.end_frame()

        except Exception:

            if render_pass is not None:

                try:
                    self.context.end_render_pass(
                        render_pass
                    )
                except Exception:
                    pass

            self.context.cancel_frame()

            raise

    # ---------------------------------------------------------
    # Run
    # ---------------------------------------------------------

    def run(self):

        self.initialize()

        try:

            while self.running:

                self.poll_events()

                self.render()

        finally:

            self.destroy()

    # ---------------------------------------------------------
    # Destroy
    # ---------------------------------------------------------

    def destroy(self):

        print()
        print("Shutting down...")

        if self.context is not None:

            try:

                self.context.wait_idle()

            except Exception:
                pass

        if self.pipeline is not None:

            try:

                sdl3.SDL_ReleaseGPUGraphicsPipeline(
                    self.context.device,
                    self.pipeline,
                )

            except Exception:
                pass

            self.pipeline = None

        if self.vertex_shader is not None:

            try:

                sdl3.SDL_ReleaseGPUShader(
                    self.context.device,
                    self.vertex_shader,
                )

            except Exception:
                pass

            self.vertex_shader = None

        if self.fragment_shader is not None:

            try:

                sdl3.SDL_ReleaseGPUShader(
                    self.context.device,
                    self.fragment_shader,
                )

            except Exception:
                pass

            self.fragment_shader = None

        if self.context is not None:

            try:
                self.context.destroy()

            except Exception:
                pass

            self.context = None

        print("Done.")


def main():

    test = VulkanBufferlessTest()
    test.run()


if __name__ == "__main__":
    main()