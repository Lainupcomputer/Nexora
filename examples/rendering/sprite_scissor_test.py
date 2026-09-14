from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.assets.manager import AssetManager
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.texture import GPUTexture
from nexora.rendering.renderer import Renderer
from nexora.threading.context import ThreadContext


ROOT = Path(__file__).resolve().parent.parent

SPRITE_PATH = (
    ROOT
    / "assets"
    / "demo_sprite.png"
)


def main() -> None:
    print("=" * 56)
    print(" Nexora GPU Sprite Scissor / Clip Test")
    print("=" * 56)
    print()

    if not SPRITE_PATH.is_file():
        raise FileNotFoundError(
            f"Sprite not found: {SPRITE_PATH}"
        )

    ThreadContext.initialize()

    context = None
    renderer = None
    asset_manager = None
    texture = None

    try:
        # ==========================================================
        # GPU context
        # ==========================================================

        print("Creating GPU context...")

        context = GPUContext(
            1280,
            720,
            title="Nexora - Sprite Scissor Test",
            debug=True,
            vsync=True,
        )

        print(
            f"GPU driver: {context.driver}"
        )

        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )

        print()

        # ==========================================================
        # Asset loading
        # ==========================================================

        print("Loading sprite...")

        asset_manager = AssetManager(
            ROOT / "assets"
        )

        image = asset_manager.load_texture(
            "demo_sprite.png"
        )

        print(
            f"Sprite size: "
            f"{image.width}x{image.height}"
        )

        # ==========================================================
        # GPU texture
        # ==========================================================

        texture = GPUTexture(
            context.device,
            image.width,
            image.height,
            data=image.pixels,
            bytes_per_pixel=image.bytes_per_pixel,
        )

        # ==========================================================
        # Renderer
        # ==========================================================

        renderer = Renderer(
            context,
        )

        print()
        print("Expected result:")
        print()
        print("  LEFT:")
        print("    Full sprite")
        print()
        print("  CENTER:")
        print("    Large sprite clipped to 260x260")
        print()
        print("  RIGHT:")
        print("    Outer clip + smaller nested clip")
        print()
        print("  BOTTOM:")
        print("    Full sprite again after pop_clip_rect()")
        print()
        print("ESC closes the test.")
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
            # TEST 1
            #
            # Unclipped sprite
            # ======================================================

            renderer.rect(
                -420.0,
                -60.0,
                300.0,
                300.0,
                color=(
                    0.12,
                    0.12,
                    0.14,
                    1.0,
                ),
            )

            renderer.sprite(
                texture,
                -420.0,
                -60.0,
                width=280.0,
                height=280.0,
            )

            # ======================================================
            # TEST 2
            #
            # Single clip
            # ======================================================

            renderer.rect(
                0.0,
                -60.0,
                260.0,
                260.0,
                color=(
                    0.12,
                    0.12,
                    0.14,
                    1.0,
                ),
            )

            # Clip is centered at:
            #
            #   x = 0
            #   y = -60
            #
            # Size:
            #
            #   260 x 260
            #
            # Top-left:
            #
            #   -130
            #   -190
            renderer.push_clip_rect(
                -130.0,
                -190.0,
                260.0,
                260.0,
            )

            # Intentionally much larger than the clip area.
            renderer.sprite(
                texture,
                0.0,
                -60.0,
                width=420.0,
                height=420.0,
            )

            renderer.pop_clip_rect()

            # ======================================================
            # TEST 3
            #
            # Nested clipping
            # ======================================================

            # Outer visual reference.
            renderer.rect(
                420.0,
                -60.0,
                320.0,
                320.0,
                color=(
                    0.12,
                    0.12,
                    0.14,
                    1.0,
                ),
            )

            # Outer clip:
            #
            # center = 420, -60
            # size   = 320, 320
            #
            # top-left:
            #
            # x = 260
            # y = -220
            renderer.push_clip_rect(
                260.0,
                -220.0,
                320.0,
                320.0,
            )

            renderer.sprite(
                texture,
                420.0,
                -60.0,
                width=420.0,
                height=420.0,
            )

            # ------------------------------------------------------
            # Nested clip
            # ------------------------------------------------------

            renderer.rect(
                420.0,
                -60.0,
                160.0,
                160.0,
                color=(
                    0.30,
                    0.18,
                    0.05,
                    1.0,
                ),
            )

            renderer.push_clip_rect(
                340.0,
                -140.0,
                160.0,
                160.0,
            )

            renderer.sprite(
                texture,
                420.0,
                -60.0,
                width=300.0,
                height=300.0,
                alpha=0.75,
                flip_x=True,
            )

            renderer.pop_clip_rect()

            # ------------------------------------------------------
            # Back to outer clip
            # ------------------------------------------------------

            renderer.sprite(
                texture,
                420.0,
                80.0,
                width=260.0,
                height=120.0,
                alpha=0.65,
                flip_y=True,
            )

            renderer.pop_clip_rect()

            # ======================================================
            # TEST 4
            #
            # Verify clipping is restored
            # ======================================================

            renderer.rect(
                0.0,
                280.0,
                300.0,
                120.0,
                color=(
                    0.12,
                    0.12,
                    0.14,
                    1.0,
                ),
            )

            renderer.sprite(
                texture,
                0.0,
                280.0,
                width=280.0,
                height=100.0,
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
        print()
        print("Cleaning up...")

        if renderer is not None:
            renderer.destroy()

        if texture is not None:
            texture.destroy()

        if asset_manager is not None:
            asset_manager.shutdown()

        if context is not None:
            context.destroy()

        print("Done.")


if __name__ == "__main__":
    main()