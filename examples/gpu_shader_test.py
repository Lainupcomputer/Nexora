from pathlib import Path

import sdl3

from nexora.rendering.gpu import GPUContext, GPUShader


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
        "Nexora GPU Shader Test",
    )

    print("GPU driver:", gpu.driver)

    vertex_shader = None
    fragment_shader = None

    try:
        vertex_shader = GPUShader(
            gpu.device,
            SHADER_DIR / "triangle.vert.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_VERTEX,
        )

        print("Vertex shader loaded")

        fragment_shader = GPUShader(
            gpu.device,
            SHADER_DIR / "triangle.frag.dxil",
            sdl3.SDL_GPU_SHADERSTAGE_FRAGMENT,
        )

        print("Fragment shader loaded")
        print("GPU shaders OK")

    finally:
        if vertex_shader:
            vertex_shader.destroy()

        if fragment_shader:
            fragment_shader.destroy()

        gpu.destroy()


if __name__ == "__main__":
    main()