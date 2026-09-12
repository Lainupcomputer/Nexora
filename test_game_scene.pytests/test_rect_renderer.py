from __future__ import annotations

import math
from pathlib import Path

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.rect_batch import GPURectBatch


def main():
    print("=" * 40)
    print(" Nexora GPU Rectangle Renderer Test")
    print("=" * 40)
    print()

    print("Creating GPU context...")

    context = GPUContext(
        1280,
        720,
        title="Nexora - GPU Rectangle Renderer Test",
        debug=True,
        vsync=True,

    )

    print(f"GPU driver: {context.driver}")
    print(
        f"Swapchain format: "
        f"{context.swapchain_format}"
    )

    shader_dir = (
        Path(__file__).resolve().parent.parent
        / "nexora"
        / "rendering"
        / "shaders"
        / "bin"
    )

    print()
    print("Creating rectangle batch...")

    renderer = GPURectBatch(
        context,
        max_rects=10000,
        vertex_shader_path=(
            shader_dir / "rect.vert.spv"
        ),
        fragment_shader_path=(
            shader_dir / "rect.frag.spv"
        ),
        camera=None,
    )

    print("Rectangle batch ready.")
    print()
    print("Controls:")
    print("  ESC / close window -> exit")
    print()

    running = True

    angle = 0.0

    try:
        while running:

            # --------------------------------------------------
            # Events
            # --------------------------------------------------

            event = sdl3.SDL_Event()

            while sdl3.SDL_PollEvent(
                event
            ):
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif (
                    event.type
                    == sdl3.SDL_EVENT_KEY_DOWN
                ):
                    if (
                        event.key.key
                        == sdl3.SDLK_ESCAPE
                    ):
                        running = False

            # --------------------------------------------------
            # Animation
            # --------------------------------------------------

            angle += 0.01

            # --------------------------------------------------
            # Begin frame
            # --------------------------------------------------

            if not context.begin_frame():
                continue

            try:
                command_buffer = (
                    context.command_buffer
                )

                # --------------------------------------------------
                # Prepare rectangles
                # --------------------------------------------------

                renderer.begin()

                # Center rectangle
                renderer.add(
                    0,
                    0,
                    300,
                    150,
                    color=(
                        1.0,
                        0.15,
                        0.15,
                        1.0,
                    ),
                    rotation=angle,
                    origin=(0.5, 0.5),
                )

                # Top-left-ish rectangle
                renderer.add(
                    -350,
                    -200,
                    180,
                    100,
                    color=(
                        0.15,
                        1.0,
                        0.15,
                        1.0,
                    ),
                    rotation=0.0,
                    origin=(0.5, 0.5),
                )

                # Bottom-right rectangle
                renderer.add(
                    350,
                    200,
                    180,
                    100,
                    color=(
                        0.15,
                        0.4,
                        1.0,
                        0.75,
                    ),
                    rotation=-angle,
                    origin=(0.5, 0.5),
                )

                # Origin test
                renderer.add(
                    -300,
                    200,
                    120,
                    120,
                    color=(
                        1.0,
                        1.0,
                        0.15,
                        1.0,
                    ),
                    rotation=0.0,
                    origin=(0.0, 0.0),
                )

                # Alpha test
                renderer.add(
                    300,
                    -200,
                    180,
                    180,
                    color=(
                        1.0,
                        0.2,
                        1.0,
                        0.35,
                    ),
                    rotation=0.0,
                    origin=(0.5, 0.5),
                )

                # --------------------------------------------------
                # Upload
                # --------------------------------------------------

                renderer.render_into(
                    command_buffer
                )

                # --------------------------------------------------
                # Render pass
                # --------------------------------------------------

                render_pass = (
                    context.begin_render_pass(
                        (
                            0.05,
                            0.05,
                            0.08,
                            1.0,
                        )
                    )
                )

                try:
                    renderer.draw_into(
                        render_pass
                    )

                finally:
                    context.end_render_pass(
                        render_pass
                    )

                # --------------------------------------------------
                # Submit
                # --------------------------------------------------

                context.end_frame()

            except Exception:
                if context.frame_active:
                    try:
                        context.cancel_frame()
                    except Exception:
                        pass

                raise

    finally:
        print()
        print("Destroying renderer...")

        renderer.destroy()

        print("Destroying GPU context...")

        context.destroy()

        print("Done.")


if __name__ == "__main__":
    main()