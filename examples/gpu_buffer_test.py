import struct

import sdl3

from nexora.rendering.gpu import (
    GPUContext,
    GPUBuffer,
)


def main():
    gpu = GPUContext(
        1280,
        720,
        "Nexora GPU Buffer Test",
    )

    buffer = None

    try:
        vertices = (
            struct.pack(
                "<ff",
                -0.7,
                -0.6,
            )
            + struct.pack(
                "<ff",
                0.7,
                -0.6,
            )
            + struct.pack(
                "<ff",
                0.0,
                0.7,
            )
        )

        buffer = GPUBuffer(
            gpu.device,
            len(vertices),
            sdl3.SDL_GPU_BUFFERUSAGE_VERTEX,
            initial_data=vertices,
        )

        print("GPU buffer created")
        print("Buffer size:", buffer.size)
        print("GPU buffer upload successful")

    finally:
        if buffer:
            buffer.destroy()

        gpu.destroy()


if __name__ == "__main__":
    main()