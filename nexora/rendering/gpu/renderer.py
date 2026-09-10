from __future__ import annotations

import struct
from pathlib import Path

import sdl3

from .buffer import GPUBuffer
from .pipeline import GPUPipeline
from .shader import GPUShader


class GPURenderer:
    """
    High-level GPU renderer for Nexora.

    Owns GPU rendering resources but does not own the GPU context.
    All SDL_GPU operations are expected to run on the main thread.
    """

    def __init__(self, context):
        self.context = context
        self.device = context.device

        self.vertex_shader = None
        self.fragment_shader = None
        self.pipeline = None
        self.vertex_buffer = None

        self._create_resources()

    @property
    def width(self) -> int:
        return self.context.swapchain_width or self.context.width

    @property
    def height(self) -> int:
        return self.context.swapchain_height or self.context.height

    def _shader_directory(self) -> Path:
        return (
            Path(__file__).resolve().parent.parent
            / "shaders"
            / "bin"
        )

    def _create_resources(self):
        shader_dir = self._shader_directory()

        self.vertex_shader = GPUShader(
            self.device,
            shader_dir / "triangle.vert.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
            sdl3.SDL_GPU_SHADERFORMAT_DXIL,
        )

        self.fragment_shader = GPUShader(
            self.device,
            shader_dir / "triangle.frag.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
            sdl3.SDL_GPU_SHADERFORMAT_DXIL,
        )

        vertices = (
            struct.pack(
                "<ff ffff",
                -0.7,
                -0.6,
                1.0,
                0.1,
                0.1,
                1.0,
            )
            + struct.pack(
                "<ff ffff",
                0.7,
                -0.6,
                0.1,
                1.0,
                0.1,
                1.0,
            )
            + struct.pack(
                "<ff ffff",
                0.0,
                0.7,
                0.1,
                0.5,
                1.0,
                1.0,
            )
        )

        self.vertex_buffer = GPUBuffer(
            self.device,
            len(vertices),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            initial_data=vertices,
        )

        vertex_description = sdl3.SDL_GPUVertexBufferDescription()
        vertex_description.slot = 0
        vertex_description.pitch = 24
        vertex_description.input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )
        vertex_description.instance_step_rate = 0

        vertex_attributes = (
            sdl3.SDL_GPUVertexAttribute * 2
        )()

        vertex_attributes[0].location = 0
        vertex_attributes[0].buffer_slot = 0
        vertex_attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        vertex_attributes[0].offset = 0

        vertex_attributes[1].location = 1
        vertex_attributes[1].buffer_slot = 0
        vertex_attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4
        )
        vertex_attributes[1].offset = 8

        vertex_descriptions = (
            sdl3.SDL_GPUVertexBufferDescription * 1
        )()
        vertex_descriptions[0] = vertex_description

        self.pipeline = GPUPipeline(
            self.device,
            vertex_shader=self.vertex_shader.shader,
            fragment_shader=self.fragment_shader.shader,
            vertex_buffer_descriptions=vertex_descriptions,
            vertex_attributes=vertex_attributes,
            primitive_type=sdl3.SDL_GPU_PRIMITIVETYPE_TRIANGLELIST,
            target_format=self.context.swapchain_format,
        )

    def begin(self, clear_color=(0.03, 0.03, 0.05, 1.0)):
        return self.context.begin_render_pass(clear_color)

    def draw_triangle(self, render_pass):
        self.pipeline.bind(render_pass)

        binding = self.vertex_buffer.binding()

        sdl3.SDL_BindGPUVertexBuffers(
            render_pass,
            0,
            binding,
            1,
        )

        sdl3.SDL_DrawGPUPrimitives(
            render_pass,
            3,
            1,
            0,
            0,
        )

    def render(self):
        if not self.context.begin_frame():
            return False

        render_pass = None

        try:
            render_pass = self.begin()

            self.draw_triangle(render_pass)

            self.context.end_render_pass(render_pass)
            render_pass = None

            self.context.end_frame()

            return True

        except Exception:
            self.context.cancel_frame()
            raise

    def run(self):
        running = True

        while running:
            for event in self.context.poll_events():
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

            self.render()

    def destroy(self):
        if self.device:
            try:
                sdl3.SDL_WaitForGPUIdle(self.device)
            except Exception:
                pass

        if self.pipeline:
            self.pipeline.destroy()
            self.pipeline = None

        if self.vertex_shader:
            self.vertex_shader.destroy()
            self.vertex_shader = None

        if self.fragment_shader:
            self.fragment_shader.destroy()
            self.fragment_shader = None

        if self.vertex_buffer:
            self.vertex_buffer.destroy()
            self.vertex_buffer = None