from __future__ import annotations

import ctypes
import struct
from pathlib import Path

import sdl3

from nexora.rendering.gpu import (
    GPUContext,
    GPUShader,
    GPUPipeline,
    GPUBuffer,
)


WIDTH = 1280
HEIGHT = 720

ROOT = Path(__file__).resolve().parents[1]

SHADER_DIR = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
)


class TexturedQuadPipelineTest:

    def __init__(self):
        self.context = None

        self.vertex_shader = None
        self.fragment_shader = None
        self.pipeline = None

        self.vertex_buffer = None

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self):

        print("========================================")
        print("NEXORA GPU PIPELINE ISOLATION TEST")
        print("========================================")
        print()

        # ------------------------------------------------------
        # GPU CONTEXT
        # ------------------------------------------------------

        print("[1/5] Creating GPU context...")

        self.context = GPUContext(
            WIDTH,
            HEIGHT,
            "Nexora GPU Pipeline Test",
        )

        print(
            "      Driver:",
            self.context.driver,
        )

        print(
            "      Swapchain format:",
            self.context.swapchain_format,
        )

        print()

        # ------------------------------------------------------
        # VERTEX SHADER
        # ------------------------------------------------------

        print("[2/5] Loading vertex shader...")

        self.vertex_shader = GPUShader(
            self.context.device,

            SHADER_DIR
            / "textured_quad.vert.dxil",

            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,

            sdl3.SDL_GPU_SHADERFORMAT_DXIL,

            num_samplers=0,
            num_storage_textures=0,
            num_storage_buffers=0,
            num_uniform_buffers=0,
        )

        print("      Vertex shader OK")
        print()

        # ------------------------------------------------------
        # FRAGMENT SHADER
        #
        # IMPORTANT:
        #
        # The temporary fragment shader has NO texture
        # and NO sampler.
        #
        # Therefore num_samplers MUST be 0.
        # ------------------------------------------------------

        print("[3/5] Loading fragment shader...")

        self.fragment_shader = GPUShader(
            self.context.device,

            SHADER_DIR
            / "textured_quad.frag.dxil",

            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,

            sdl3.SDL_GPU_SHADERFORMAT_DXIL,

            num_samplers=0,
            num_storage_textures=0,
            num_storage_buffers=0,
            num_uniform_buffers=0,
        )

        print("      Fragment shader OK")
        print()

        # ------------------------------------------------------
        # VERTEX BUFFER
        # ------------------------------------------------------

        print("[4/5] Creating vertex buffer...")

        self._create_quad()

        print(
            "      Vertex buffer:",
            len(self._vertices),
            "bytes",
        )

        print()

        # ------------------------------------------------------
        # PIPELINE
        # ------------------------------------------------------

        print("[5/5] Creating graphics pipeline...")

        self._create_pipeline()

        print()
        print("========================================")
        print("PIPELINE CREATED SUCCESSFULLY")
        print("========================================")
        print()
        print("If the window shows a pink quad,")
        print("the pipeline and vertex layout work.")
        print()
        print("Close the window to exit.")
        print()

    # ==========================================================
    # CREATE QUAD
    # ==========================================================

    def _create_quad(self):

        """
        Two triangles.

        Vertex:

            float2 position
            float2 uv

        Stride:

            16 bytes
        """

        vertices = (

            # ==================================================
            # TRIANGLE 1
            # ==================================================

            # Top-left
            struct.pack(
                "<ffff",
                -0.7,
                 0.7,
                 0.0,
                 0.0,
            )

            +

            # Top-right
            struct.pack(
                "<ffff",
                 0.7,
                 0.7,
                 1.0,
                 0.0,
            )

            +

            # Bottom-left
            struct.pack(
                "<ffff",
                -0.7,
                -0.7,
                 0.0,
                 1.0,
            )

            # ==================================================
            # TRIANGLE 2
            # ==================================================

            +

            # Top-right
            struct.pack(
                "<ffff",
                 0.7,
                 0.7,
                 1.0,
                 0.0,
            )

            +

            # Bottom-right
            struct.pack(
                "<ffff",
                 0.7,
                -0.7,
                 1.0,
                 1.0,
            )

            +

            # Bottom-left
            struct.pack(
                "<ffff",
                -0.7,
                -0.7,
                 0.0,
                 1.0,
            )
        )

        self._vertices = vertices

        self.vertex_buffer = GPUBuffer(
            self.context.device,

            len(vertices),

            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,

            initial_data=vertices,
        )

    # ==========================================================
    # CREATE PIPELINE
    # ==========================================================

    def _create_pipeline(self):

        # ------------------------------------------------------
        # VERTEX BUFFER DESCRIPTION
        # ------------------------------------------------------

        vertex_description = (
            sdl3.SDL_GPUVertexBufferDescription()
        )

        vertex_description.slot = 0

        # float2 position = 8 bytes
        # float2 uv       = 8 bytes
        #
        # Total           = 16 bytes

        vertex_description.pitch = 16

        vertex_description.input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )

        vertex_description.instance_step_rate = 0

        # ------------------------------------------------------
        # ATTRIBUTES
        # ------------------------------------------------------

        vertex_attributes = (
            sdl3.SDL_GPUVertexAttribute * 2
        )()

        # ------------------------------------------------------
        # LOCATION 0
        #
        # position : float2
        # offset   : 0
        # ------------------------------------------------------

        vertex_attributes[0].location = 0

        vertex_attributes[0].buffer_slot = 0

        vertex_attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )

        vertex_attributes[0].offset = 0

        # ------------------------------------------------------
        # LOCATION 1
        #
        # uv : float2
        # offset : 8
        # ------------------------------------------------------

        vertex_attributes[1].location = 1

        vertex_attributes[1].buffer_slot = 0

        vertex_attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )

        vertex_attributes[1].offset = 8

        # ------------------------------------------------------
        # ARRAY
        # ------------------------------------------------------

        vertex_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription * 1
        )()

        vertex_descriptions[0] = (
            vertex_description
        )

        # ------------------------------------------------------
        # PIPELINE
        # ------------------------------------------------------

        self.pipeline = GPUPipeline(

            self.context.device,

            vertex_shader=(
                self.vertex_shader.shader
            ),

            fragment_shader=(
                self.fragment_shader.shader
            ),

            vertex_buffer_descriptions=(
                vertex_descriptions
            ),

            vertex_attributes=(
                vertex_attributes
            ),

            primitive_type=(
                sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST
            ),

            target_format=(
                self.context.swapchain_format
            ),
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(self):

        if not self.context.begin_frame():
            return

        render_pass = None

        try:

            # --------------------------------------------------
            # CLEAR
            # --------------------------------------------------

            render_pass = (
                self.context.begin_render_pass(
                    (
                        0.03,
                        0.03,
                        0.05,
                        1.0,
                    )
                )
            )

            # --------------------------------------------------
            # PIPELINE
            # --------------------------------------------------

            self.pipeline.bind(
                render_pass
            )

            # --------------------------------------------------
            # VERTEX BUFFER
            # --------------------------------------------------

            vertex_binding = (
                self.vertex_buffer.binding()
            )

            sdl3.SDL_BindGPUVertexBuffers(

                render_pass,

                0,

                ctypes.byref(
                    vertex_binding
                ),

                1,
            )

            # --------------------------------------------------
            # DRAW
            # --------------------------------------------------

            sdl3.SDL_DrawGPUPrimitives(

                render_pass,

                # vertex count
                6,

                # instance count
                1,

                # first vertex
                0,

                # first instance
                0,
            )

            # --------------------------------------------------
            # END PASS
            # --------------------------------------------------

            self.context.end_render_pass(
                render_pass
            )

            render_pass = None

            # --------------------------------------------------
            # SUBMIT
            # --------------------------------------------------

            self.context.end_frame()

        except Exception:

            if render_pass:
                try:
                    self.context.end_render_pass(
                        render_pass
                    )
                except Exception:
                    pass

            self.context.cancel_frame()

            raise

    # ==========================================================
    # RUN
    # ==========================================================

    def run(self):

        running = True

        while running:

            for event in self.context.poll_events():

                if event.type == (
                    sdl3.SDL_EVENT_QUIT
                ):
                    running = False

            self.render()

    # ==========================================================
    # DESTROY
    # ==========================================================

    def destroy(self):

        if (
            self.context
            and self.context.device
        ):
            try:

                sdl3.SDL_WaitForGPUIdle(
                    self.context.device
                )

            except Exception:
                pass

        # ------------------------------------------------------
        # PIPELINE
        # ------------------------------------------------------

        if self.pipeline:

            self.pipeline.destroy()

            self.pipeline = None

        # ------------------------------------------------------
        # SHADERS
        # ------------------------------------------------------

        if self.vertex_shader:

            self.vertex_shader.destroy()

            self.vertex_shader = None

        if self.fragment_shader:

            self.fragment_shader.destroy()

            self.fragment_shader = None

        # ------------------------------------------------------
        # BUFFER
        # ------------------------------------------------------

        if self.vertex_buffer:

            self.vertex_buffer.destroy()

            self.vertex_buffer = None

        # ------------------------------------------------------
        # CONTEXT
        # ------------------------------------------------------

        if self.context:

            self.context.destroy()

            self.context = None


# ==============================================================
# MAIN
# ==============================================================

def main():

    app = TexturedQuadPipelineTest()

    try:

        app.initialize()

        app.run()

    finally:

        app.destroy()


if __name__ == "__main__":
    main()