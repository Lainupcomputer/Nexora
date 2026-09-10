from __future__ import annotations

import ctypes
from pathlib import Path

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.shader import GPUShader


BASE_DIR = Path(__file__).resolve().parent.parent
SHADER_DIR = (
    BASE_DIR
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
)


class BufferlessPipelineTest:
    def __init__(self):
        self.context: GPUContext | None = None

        self.vertex_shader: GPUShader | None = None
        self.fragment_shader: GPUShader | None = None

        self.pipeline = None

        self.running = True

    def _check(self, condition, message):
        if not condition:
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"{message}: {error}"
            )

    def initialize(self):
        print("=" * 50)
        print("NEXORA BUFFERLESS GPU PIPELINE TEST")
        print("=" * 50)

        # ==================================================
        # GPU CONTEXT
        # ==================================================

        print()
        print("[1/4] Creating GPU context...")

        self.context = GPUContext(
            1280,
            720,
            "Nexora Bufferless Pipeline Test",
            debug=True,
            frames_in_flight=2,
        )

        print(
            f"      Driver: "
            f"{self.context.driver}"
        )

        print(
            f"      Swapchain format: "
            f"{self.context.swapchain_format}"
        )

        # ==================================================
        # VERTEX SHADER
        # ==================================================

        print()
        print("[2/4] Loading vertex shader...")

        vertex_shader_path = (
            SHADER_DIR
            / "bufferless.vert.dxil"
        )

        if not vertex_shader_path.exists():
            raise FileNotFoundError(
                f"Vertex shader not found: "
                f"{vertex_shader_path}"
            )

        self.vertex_shader = GPUShader(
            self.context.device,
            vertex_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
            shader_format=sdl3.SDL_GPU_SHADERFORMAT_DXIL,
            entrypoint="main",
            num_samplers=0,
            num_storage_textures=0,
            num_storage_buffers=0,
            num_uniform_buffers=0,
        )

        print("      Vertex shader OK")

        # ==================================================
        # FRAGMENT SHADER
        # ==================================================

        print()
        print("[3/4] Loading fragment shader...")

        fragment_shader_path = (
            SHADER_DIR
            / "bufferless.frag.dxil"
        )

        if not fragment_shader_path.exists():
            raise FileNotFoundError(
                f"Fragment shader not found: "
                f"{fragment_shader_path}"
            )

        self.fragment_shader = GPUShader(
            self.context.device,
            fragment_shader_path,
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
            shader_format=sdl3.SDL_GPU_SHADERFORMAT_DXIL,
            entrypoint="main",
            num_samplers=0,
            num_storage_textures=0,
            num_storage_buffers=0,
            num_uniform_buffers=0,
        )

        print("      Fragment shader OK")

        # ==================================================
        # GRAPHICS PIPELINE
        # ==================================================

        print()
        print(
            "[4/4] Creating bufferless "
            "graphics pipeline..."
        )

        # --------------------------------------------------
        # Vertex input
        #
        # IMPORTANT:
        # No vertex buffers.
        # No vertex attributes.
        #
        # The vertex shader uses SV_VertexID.
        # --------------------------------------------------

        vertex_input = (
            sdl3.SDL_GPUVertexInputState()
        )

        vertex_input.vertex_buffer_descriptions = None
        vertex_input.num_vertex_buffers = 0

        vertex_input.vertex_attributes = None
        vertex_input.num_vertex_attributes = 0

        # --------------------------------------------------
        # Rasterizer
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Multisampling
        # --------------------------------------------------

        multisample = (
            sdl3.SDL_GPUMultisampleState()
        )

        multisample.sample_count = (
            sdl3.SDL_GPU_SAMPLECOUNT_1
        )

        multisample.sample_mask = 0
        multisample.enable_mask = False
        multisample.enable_alpha_to_coverage = False

        # --------------------------------------------------
        # Depth / stencil
        # --------------------------------------------------

        depth = (
            sdl3.SDL_GPUDepthStencilState()
        )

        depth.enable_depth_test = False
        depth.enable_depth_write = False
        depth.enable_stencil_test = False

        # --------------------------------------------------
        # Color target
        # --------------------------------------------------

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
        #
        # `SDL_GPUColorTargetDescription * 1`
        # creates an ARRAY TYPE.
        #
        # We need to instantiate the array with ().
        #
        color_targets = (
            sdl3.SDL_GPUColorTargetDescription * 1
        )()

        color_targets[0] = color_target

        # --------------------------------------------------
        # Pipeline target info
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Pipeline create info
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Create pipeline
        # --------------------------------------------------

        self.pipeline = (
            sdl3.SDL_CreateGPUGraphicsPipeline(
                self.context.device,
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
                "SDL_CreateGPUGraphicsPipeline "
                "failed: "
                f"{error}"
            )

        print(
            "      Bufferless pipeline OK"
        )

    def run(self):
        print()
        print(
            "Starting render loop..."
        )
        print(
            "Close the window to exit."
        )

        while self.running:
            self._poll_events()

            if not self.context.begin_frame():
                continue

            render_pass = None

            try:
                # ------------------------------------------
                # Begin render pass
                # ------------------------------------------

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

                # ------------------------------------------
                # Bind pipeline
                # ------------------------------------------

                sdl3.SDL_BindGPUGraphicsPipeline(
                    render_pass,
                    self.pipeline,
                )

                # ------------------------------------------
                # Draw bufferless triangle
                #
                # Vertex shader creates all vertices
                # using SV_VertexID.
                # ------------------------------------------

                sdl3.SDL_DrawGPUPrimitives(
                    render_pass,
                    3,
                    1,
                    0,
                    0,
                )

                # ------------------------------------------
                # End render pass
                # ------------------------------------------

                self.context.end_render_pass(
                    render_pass
                )

                render_pass = None

                # ------------------------------------------
                # Submit frame
                # ------------------------------------------

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

    def _poll_events(self):
        event = sdl3.SDL_Event()

        while sdl3.SDL_PollEvent(
            ctypes.byref(event)
        ):
            if event.type == sdl3.SDL_EVENT_QUIT:
                self.running = False

    def destroy(self):
        print()
        print("Cleaning up...")

        # ==================================================
        # Wait for GPU
        # ==================================================

        if self.context:
            try:
                self.context.wait_idle()
            except Exception:
                pass

        # ==================================================
        # Pipeline
        # ==================================================

        if self.pipeline:
            sdl3.SDL_ReleaseGPUGraphicsPipeline(
                self.context.device,
                self.pipeline,
            )

            self.pipeline = None

        # ==================================================
        # Vertex shader
        # ==================================================

        if self.vertex_shader:
            self.vertex_shader.destroy()
            self.vertex_shader = None

        # ==================================================
        # Fragment shader
        # ==================================================

        if self.fragment_shader:
            self.fragment_shader.destroy()
            self.fragment_shader = None

        # ==================================================
        # GPU context
        # ==================================================

        if self.context:
            self.context.destroy()
            self.context = None

        print("Done.")

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()


def main():
    app = BufferlessPipelineTest()

    try:
        app.initialize()
        app.run()

    finally:
        app.destroy()


if __name__ == "__main__":
    main()