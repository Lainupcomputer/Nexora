from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.text_renderer import GPUTextRenderer
from nexora.rendering.text import TextSystem


ROOT = Path(__file__).resolve().parent.parent

FONT_PATH = (
    ROOT
    / "assets"
    / "fonts"
    / "DejaVuSans.ttf"
)


def main() -> None:
    print("=" * 40)
    print(" Nexora GPU Text Renderer Test")
    print("=" * 40)
    print()

    if not FONT_PATH.is_file():
        raise FileNotFoundError(
            f"Font not found: {FONT_PATH}"
        )

    text_system = TextSystem()
    text_system.initialize()

    context = None
    font = None
    renderer = None

    try:
        print("Creating GPU context...")

        context = GPUContext(
            1280,
            720,
            title="Nexora - GPU Text Renderer Test",
            debug=True,
            vsync=True,
        )

        print(f"GPU driver: {context.driver}")
        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )
        print()

        print("Loading font...")

        font = text_system.font(
            FONT_PATH,
            32,
        )

        print(f"Font: {font.path}")
        print(f"Size: {font.size}")
        print(f"Height: {font.height}")
        print(f"Ascent: {font.ascent}")
        print(f"Descent: {font.descent}")
        print(f"Line skip: {font.line_skip}")
        print()

        print("Creating GPU text renderer...")

        renderer = GPUTextRenderer(
            context,
            font,
            atlas_width=1024,
            atlas_height=1024,
            atlas_padding=2,
        )

        print(
            f"Atlas glyphs: "
            f"{renderer.atlas.glyph_count}"
        )

        print(
            f"Atlas texture: "
            f"{renderer.atlas_texture.texture}"
        )

        print()
        print("Rendering test scene...")
        print("Close the window to finish.")
        print()

        running = True

        while running:
            for event in context.poll_events():
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif event.type == sdl3.SDL_EVENT_KEY_DOWN:
                    if event.key.key == sdl3.SDLK_ESCAPE:
                        running = False

            if not running:
                break

            if not context.begin_frame():
                time.sleep(0.001)
                continue

            try:
                command_buffer = (
                    context.command_buffer
                )

                renderer.clear()

                # --------------------------------------------------
                # White headline
                # --------------------------------------------------

                renderer.set_color(
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                )

                renderer.draw(
                    "Nexora Engine",
                    0,
                    0,
                    scale=1.5,
                )

                # --------------------------------------------------
                # Normal text
                # --------------------------------------------------

                renderer.set_color(
                    0.8,
                    0.8,
                    0.8,
                    1.0,
                )

                renderer.draw(
                    "GPU Font Renderer",
                    80,
                    170,
                )

                # --------------------------------------------------
                # German / UTF-8 characters
                # --------------------------------------------------

                renderer.set_color(
                    0.4,
                    1.0,
                    0.7,
                    1.0,
                )

                renderer.draw(
                    "ÄÖÜ äöü ß €",
                    80,
                    220,
                )

                # --------------------------------------------------
                # Different scale
                # --------------------------------------------------

                renderer.set_color(
                    1.0,
                    0.7,
                    0.3,
                    1.0,
                )

                renderer.draw(
                    "Scale 0.75",
                    80,
                    280,
                    scale=0.75,
                )

                renderer.draw(
                    "Scale 2.0",
                    80,
                    360,
                    scale=2.0,
                )

                # --------------------------------------------------
                # Rotation
                # --------------------------------------------------

                renderer.set_color(
                    0.8,
                    0.5,
                    1.0,
                    1.0,
                )

                renderer.draw(
                    "Rotated",
                    500,
                    300,
                    rotation=0.15,
                    scale=1.2,
                )

                # --------------------------------------------------
                # Multiline text
                # --------------------------------------------------

                renderer.set_color(
                    0.5,
                    0.8,
                    1.0,
                    1.0,
                )

                renderer.draw(
                    "Line one\n"
                    "Line two\n"
                    "Line three",
                    700,
                    150,
                )

                # --------------------------------------------------
                # Alpha
                # --------------------------------------------------

                renderer.set_color(
                    1.0,
                    1.0,
                    1.0,
                    0.5,
                )

                renderer.draw(
                    "50% alpha",
                    700,
                    300,
                    scale=1.5,
                )

                # --------------------------------------------------
                # Upload instances
                # --------------------------------------------------

                renderer.render_into(
                    command_buffer
                )

                # --------------------------------------------------
                # Render pass
                # --------------------------------------------------

                render_pass = (
                    context.begin_render_pass(
                        (0.03, 0.03, 0.04, 1.0)
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

                context.end_frame()

            except Exception:
                context.cancel_frame()
                raise

            time.sleep(0.001)

    finally:
        print()
        print("Cleaning up...")

        if renderer is not None:
            renderer.destroy()

        if font is not None:
            font.close()

        if context is not None:
            context.destroy()

        text_system.shutdown()

        print("Done.")


if __name__ == "__main__":
    main()

