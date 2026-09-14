from __future__ import annotations

import time

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.threading.context import ThreadContext


def main() -> None:
    print("=" * 50)
    print(" Nexora GPU Scissor / Clip Test")
    print("=" * 50)
    print()

    ThreadContext.initialize()

    context = None
    renderer = None

    try:
        # ==========================================================
        # GPU Context
        # ==========================================================

        print("Creating GPU context...")

        context = GPUContext(
            1280,
            720,
            title="Nexora - GPU Scissor Test",
            debug=True,
            vsync=True,
        )

        print(f"GPU driver: {context.driver}")
        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )
        print()

        # ==========================================================
        # Renderer
        # ==========================================================

        print("Creating renderer...")

        renderer = Renderer(
            context,
        )

        print()
        print("Expected result:")
        print()
        print("  LEFT:")
        print("    Large red rectangle")
        print("    No clipping")
        print()
        print("  CENTER:")
        print("    Green 420x420 rectangle")
        print("    clipped to 260x260")
        print()
        print("  RIGHT:")
        print("    Blue outer clip")
        print("    Yellow nested clip")
        print()
        print("  BOTTOM:")
        print("    White bar is NOT clipped")
        print()
        print("Press ESC or close the window.")
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

                elif (
                    event.type
                    == sdl3.SDL_EVENT_KEY_DOWN
                ):
                    if (
                        event.key.key
                        == sdl3.SDLK_ESCAPE
                    ):
                        running = False

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

            try:
                # ==================================================
                # Background
                # ==================================================

                renderer.rect(
                    0.0,
                    0.0,
                    1280.0,
                    720.0,
                    color=(
                        0.05,
                        0.05,
                        0.06,
                        1.0,
                    ),
                )

                # ==================================================
                # TEST 1
                #
                # Unclipped red rectangle
                # ==================================================

                renderer.rect(
                    -420.0,
                    0.0,
                    260.0,
                    420.0,
                    color=(
                        0.8,
                        0.15,
                        0.15,
                        1.0,
                    ),
                )

                # ==================================================
                # TEST 2
                #
                # Center green rectangle
                #
                # IMPORTANT:
                #
                # Clip coordinates use Nexora coordinates:
                #
                #     0,0 = screen center
                #
                # x/y describe the TOP-LEFT of the clip rectangle.
                #
                # A centered 260x260 clip therefore begins at:
                #
                #     -130, -130
                # ==================================================

                renderer.push_clip_rect(
                    -130.0,
                    -130.0,
                    260.0,
                    260.0,
                )

                # Large 420x420 rectangle.
                #
                # Only the centered 260x260 section should remain
                # visible.
                renderer.rect(
                    0.0,
                    0.0,
                    420.0,
                    420.0,
                    color=(
                        0.15,
                        0.75,
                        0.25,
                        1.0,
                    ),
                )

                renderer.pop_clip_rect()

                # ==================================================
                # TEST 3
                #
                # Right side nested clipping
                # ==================================================

                # Blue rectangle center:
                #
                #     x = 420
                #     y = 0
                #
                # Outer clip:
                #
                #     320 x 320
                #
                # Top-left therefore:
                #
                #     x = 420 - 160 = 260
                #     y =   0 - 160 = -160

                renderer.push_clip_rect(
                    260.0,
                    -160.0,
                    320.0,
                    320.0,
                )

                renderer.rect(
                    420.0,
                    0.0,
                    420.0,
                    420.0,
                    color=(
                        0.15,
                        0.3,
                        0.85,
                        1.0,
                    ),
                )

                # --------------------------------------------------
                # Nested yellow clip
                # --------------------------------------------------
                #
                # 160x160 area centered at x=420, y=0:
                #
                # top-left:
                #
                #     340, -80
                # --------------------------------------------------

                renderer.push_clip_rect(
                    340.0,
                    -80.0,
                    160.0,
                    160.0,
                )

                renderer.rect(
                    420.0,
                    0.0,
                    360.0,
                    360.0,
                    color=(
                        0.95,
                        0.8,
                        0.1,
                        1.0,
                    ),
                )

                renderer.pop_clip_rect()

                # --------------------------------------------------
                # Outer clip is active again
                # --------------------------------------------------

                renderer.rect(
                    420.0,
                    110.0,
                    260.0,
                    70.0,
                    color=(
                        0.8,
                        0.2,
                        0.8,
                        1.0,
                    ),
                )

                renderer.pop_clip_rect()

                # ==================================================
                # TEST 4
                #
                # Clipping must be disabled again.
                # ==================================================

                renderer.rect(
                    0.0,
                    300.0,
                    900.0,
                    40.0,
                    color=(
                        0.8,
                        0.8,
                        0.8,
                        1.0,
                    ),
                )

                # ==================================================
                # End frame
                # ==================================================

                if not renderer.end_frame():
                    break

            except Exception:
                raise

            time.sleep(
                0.001
            )

    finally:
        print()
        print("Cleaning up...")

        if renderer is not None:
            renderer.destroy()

        if context is not None:
            context.destroy()

        print("Done.")


if __name__ == "__main__":
    main()