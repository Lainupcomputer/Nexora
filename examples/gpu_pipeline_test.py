import ctypes
from pathlib import Path

import sdl3

from nexora.rendering.gpu import (
    GPUContext,
    GPUShader,
    GPUPipeline,
)


ROOT = Path(__file__).resolve().parents[1]

SHADER_DIR = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
)


def main():
    gpu = GPUContext(
        1280,
        720,
        "Nexora GPU Pipeline Test",
    )

    vertex_shader = None
    fragment_shader = None
    pipeline = None

    try:
        vertex_shader = GPUShader(
            gpu.device,
            SHADER_DIR / "triangle.vert.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
        )

        fragment_shader = GPUShader(
            gpu.device,
            SHADER_DIR / "triangle.frag.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
        )

        # One vertex buffer:
        #
        # position = float2 = 8 bytes
        # color    = float4 = 16 bytes
        #
        # stride = 24 bytes

        vertex_buffers = (
            sdl3.SDL_GPUVertexBufferDescription * 1
        )()

        vertex_buffers[0].slot = 0
        vertex_buffers[0].pitch = 24
        vertex_buffers[0].input_rate = (
            sdl3.SDL_GPU_VERTEXINPUTRATE_VERTEX
        )
        vertex_buffers[0].instance_step_rate = 0

        attributes = (
            sdl3.SDL_GPUVertexAttribute * 2
        )()

        attributes[0].location = 0
        attributes[0].buffer_slot = 0
        attributes[0].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2
        )
        attributes[0].offset = 0

        attributes[1].location = 1
        attributes[1].buffer_slot = 0
        attributes[1].format = (
            sdl3.SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4
        )
        attributes[1].offset = 8

        pipeline = GPUPipeline(
            gpu.device,
            vertex_shader=vertex_shader.shader,
            fragment_shader=fragment_shader.shader,
            vertex_buffer_descriptions=vertex_buffers,
            vertex_attributes=attributes,
            target_format=gpu.swapchain_format,
        )

        print("GPU pipeline created successfully")

    finally:
        if pipeline:
            pipeline.destroy()

        if vertex_shader:
            vertex_shader.destroy()

        if fragment_shader:
            fragment_shader.destroy()

        gpu.destroy()


if __name__ == "__main__":
    main()