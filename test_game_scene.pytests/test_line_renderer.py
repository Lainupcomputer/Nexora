from __future__ import annotations

from pathlib import Path

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.line_batch import GPULineBatch


def main() -> None:
    print("=" * 40)
    print(" Nexora GPU Line Renderer Test")
    print("=" * 40)
    print()

    print("Creating GPU context...")

    context = GPUContext(
        1280,
        720,
        title="Nexora - Line Renderer Test",
        debug=True,
        vsync=True,
    )

    print(f"GPU driver: {context.driver}")
    print(f"Swapchain format: {context.swapchain_format}")
    print()

    shader_dir = (
        Path(__file__).resolve().parent.parent
        / "nexora"
        / "rendering"
        / "shaders"
        / "bin"
    )

    print("Creating line batch...")

    renderer = GPULineBatch(
        context,
        max_lines=10000,
        vertex_shader_path=shader_dir / "line.vert.spv",
        fragment_shader_path=shader_dir / "line.frag.spv",
        camera=None,
    )

    print("Line batch ready.")
    print()
    print("Press ESC or close the window to exit.")
    print()

    running = True

    try:
        while running:

            # ---------------------------------------------------------
            # Events
            # ---------------------------------------------------------

            for event in context.poll_events():

                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif (
                    event.type == sdl3.SDL_EVENT_KEY_DOWN
                    and event.key.key == sdl3.SDLK_ESCAPE
                ):
                    running = False

            if not running:
                break

            # ---------------------------------------------------------
            # Begin frame
            # ---------------------------------------------------------

            if not context.begin_frame():
                continue

            command_buffer = context.command_buffer

            # ---------------------------------------------------------
            # Build lines
            # ---------------------------------------------------------

            renderer.begin()

            # Horizontal
            renderer.add(
                -500,
                -250,
                500,
                -250,
                width=4,
                color=(1.0, 0.0, 0.0, 1.0),
            )

            # Vertical
            renderer.add(
                -500,
                -250,
                -500,
                250,
                width=4,
                color=(0.0, 1.0, 0.0, 1.0),
            )

            # Diagonal
            renderer.add(
                -500,
                250,
                500,
                -250,
                width=6,
                color=(0.0, 0.5, 1.0, 1.0),
            )

            # Opposite diagonal
            renderer.add(
                -500,
                -250,
                500,
                250,
                width=6,
                color=(1.0, 1.0, 0.0, 1.0),
            )

            # Center horizontal
            renderer.add(
                -150,
                0,
                150,
                0,
                width=10,
                color=(1.0, 1.0, 1.0, 1.0),
            )

            # Center vertical
            renderer.add(
                0,
                -150,
                0,
                150,
                width=10,
                color=(1.0, 1.0, 1.0, 1.0),
            )

            # ---------------------------------------------------------
            # Upload line data
            # ---------------------------------------------------------

            renderer.render_into(command_buffer)

            # ---------------------------------------------------------
            # Render pass
            # ---------------------------------------------------------

            render_pass = context.begin_render_pass(
                clear_color=(0.05, 0.05, 0.05, 1.0),
            )

            renderer.draw_into(render_pass)

            context.end_render_pass(render_pass)

            # ---------------------------------------------------------
            # Submit
            # ---------------------------------------------------------

            context.end_frame()

    except Exception:
        # Never leave an acquired command buffer alive after an error.
        if context.frame_active:
            context.cancel_frame()

        raise

    finally:
        print("Destroying line renderer...")
        renderer.destroy()

        print("Destroying GPU context...")
        context.destroy()

        print("Done.")


if __name__ == "__main__":
    main()