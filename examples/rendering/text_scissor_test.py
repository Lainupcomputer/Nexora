from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.rendering.text import TextSystem
from nexora.threading.context import ThreadContext


# ==============================================================
# Paths
# ==============================================================

ROOT = Path(__file__).resolve().parent.parent

FONT_PATH = (
    ROOT
    / "assets"
    / "fonts"
    / "Roboto-Regular.ttf"
)


# ==============================================================
# Main
# ==============================================================


def main() -> None:
    print("=" * 58)
    print(" Nexora GPU Text Scissor / Clip Test")
    print("=" * 58)
    print()

    if not FONT_PATH.is_file():
        raise FileNotFoundError(
            f"Font not found: {FONT_PATH}"
        )

    ThreadContext.initialize()

    context = None
    renderer = None
    text_system = None
    font = None

    try:
        # ==========================================================
        # GPU context
        # ==========================================================

        print("Creating GPU context...")

        context = GPUContext(
            1280,
            720,
            title="Nexora - Text Scissor Test",
            debug=True,
            vsync=True,
        )

        print(
            f"GPU driver: {context.driver}"
        )

        print(
            "Swapchain format:",
            context.swapchain_format,
        )

        print()

        # ==========================================================
        # Text
        # ==========================================================

        print("Loading font...")

        text_system = TextSystem()

        font = text_system.font(
            FONT_PATH,
            32,
        )

        print(
            f"Font: {font.path}"
        )

        print(
            f"Size: {font.size}"
        )

        print(
            f"Height: {font.height}"
        )

        print(
            f"Ascent: {font.ascent}"
        )

        print(
            f"Descent: {font.descent}"
        )

        print()

        # ==========================================================
        # Renderer
        # ==========================================================

        print("Creating renderer...")

        renderer = Renderer(
            context,
            font=font,
        )

        print()
        print("Expected result:")
        print()
        print(
            "  TOP:"
        )
        print(
            "    Full unclipped text."
        )
        print()
        print(
            "  CENTER:"
        )
        print(
            "    Long text cut to the dark rectangle."
        )
        print()
        print(
            "  BOTTOM:"
        )
        print(
            "    Text cut by a nested smaller clip."
        )
        print()
        print(
            "  VERY BOTTOM:"
        )
        print(
            "    Full text again after all pop_clip_rect calls."
        )
        print()
        print(
            "ESC closes the test."
        )
        print()

        running = True

        while running:
            # ======================================================
            # Events
            # ======================================================

            events = list(
                context.poll_events()
            )

            for event in events:
                if (
                    event.type
                    == sdl3.SDL_EVENT_QUIT
                ):
                    running = False
                    break

                if (
                    event.type
                    == sdl3.SDL_EVENT_KEY_DOWN
                ):
                    if (
                        event.key.key
                        == sdl3.SDLK_ESCAPE
                    ):
                        running = False
                        break

            if not running:
                break

            # ======================================================
            # Begin frame
            # ======================================================

            if not renderer.begin_frame():
                time.sleep(
                    0.001
                )
                continue

            # ======================================================
            # Background
            # ======================================================

            renderer.rect(
                0.0,
                0.0,
                1280.0,
                720.0,
                color=(
                    0.04,
                    0.04,
                    0.05,
                    1.0,
                ),
            )

            # ======================================================
            # Test 1
            #
            # Unclipped text
            # ======================================================

            renderer.text(
                "UNCLIPPED TEXT - THIS SHOULD BE COMPLETELY VISIBLE",
                -500.0,
                -220.0,
            )

            # ======================================================
            # Test 2
            #
            # Single clip
            # ======================================================

            # Visible reference rectangle.
            #
            # Rectangle itself is centered at 0, 0.
            renderer.rect(
                0.0,
                0.0,
                420.0,
                110.0,
                color=(
                    0.12,
                    0.12,
                    0.14,
                    1.0,
                ),
            )

            # The clip rectangle uses TOP-LEFT coordinates
            # in Nexora's centered coordinate system.
            #
            # 420 x 110 centered on screen:
            #
            # x = -210
            # y = -55
            renderer.push_clip_rect(
                -210.0,
                -55.0,
                420.0,
                110.0,
            )

            # Intentionally starts well outside the clip.
            renderer.text(
                "<<< THIS TEXT STARTS OUTSIDE AND CONTINUES FAR OUTSIDE >>>",
                -420.0,
                10.0,
            )

            renderer.pop_clip_rect()

            # ======================================================
            # Test 3
            #
            # Outer clip
            # ======================================================

            renderer.rect(
                0.0,
                190.0,
                600.0,
                120.0,
                color=(
                    0.10,
                    0.11,
                    0.15,
                    1.0,
                ),
            )

            # 600 x 120 box centered at:
            #
            # x = 0
            # y = 190
            #
            # Top-left:
            #
            # -300, 130
            renderer.push_clip_rect(
                -300.0,
                130.0,
                600.0,
                120.0,
            )

            renderer.text(
                "OUTER CLIP - THIS TEXT IS LIMITED TO THE LARGE BOX",
                -380.0,
                200.0,
            )

            # ======================================================
            # Test 3b
            #
            # Nested clip
            # ======================================================

            # Inner visual reference rectangle.
            renderer.rect(
                0.0,
                215.0,
                180.0,
                60.0,
                color=(
                    0.25,
                    0.18,
                    0.08,
                    1.0,
                ),
            )

            # Inner box:
            #
            # center:
            #     0, 215
            #
            # size:
            #     180 x 60
            #
            # top-left:
            #     -90, 185
            renderer.push_clip_rect(
                -90.0,
                185.0,
                180.0,
                60.0,
            )

            renderer.text(
                "NESTED TEXT SHOULD BE CUT VERY HARD",
                -220.0,
                225.0,
            )

            # Back to outer clip.
            renderer.pop_clip_rect()

            # Back to no clipping.
            renderer.pop_clip_rect()

            # ======================================================
            # Test 4
            #
            # Verify clipping is restored
            # ======================================================

            renderer.text(
                "CLIP STACK RESTORED - THIS LINE SHOULD BE FULLY VISIBLE",
                -470.0,
                315.0,
            )

            # ======================================================
            # End frame
            # ======================================================

            if not renderer.end_frame():
                break

            time.sleep(
                0.001
            )

    finally:
        # ==========================================================
        # Cleanup
        # ==========================================================

        print()
        print("Cleaning up...")

        if renderer is not None:
            renderer.destroy()

        if font is not None:
            font.close()

        if text_system is not None:
            text_system.shutdown()

        if context is not None:
            context.destroy()

        print("Done.")


if __name__ == "__main__":
    main()