from __future__ import annotations

import time

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.renderer import GPURenderer


# ==============================================================
# CONFIG
# ==============================================================

WIDTH = 1280
HEIGHT = 720

TARGET_FPS = 144


# --------------------------------------------------------------
# Test modes
#
# 1:
#     GPURenderer
#     post-processing OFF
#
# 2:
#     GPURenderer
#     post-processing ON
#
# Start with MODE = 1.
# --------------------------------------------------------------

MODE = 2


# ==============================================================
# MAIN
# ==============================================================


def main() -> None:
    print()
    print("=" * 64)
    print(" Nexora GPURenderer Memory Test")
    print("=" * 64)
    print()

    print(
        f"Resolution: "
        f"{WIDTH}x{HEIGHT}"
    )

    print(
        f"Target FPS: "
        f"{TARGET_FPS}"
    )

    print(
        f"Mode: "
        f"{MODE}"
    )

    print()

    # ==========================================================
    # GPU CONTEXT
    # ==============================================================

    context = GPUContext(
        WIDTH,
        HEIGHT,
        title="Nexora - GPURenderer Memory Test",
        debug=True,
        frames_in_flight=2,
        vsync=False,
        resizable=True,
    )

    print(
        f"GPU driver: "
        f"{context.driver}"
    )

    # ==========================================================
    # GPU RENDERER
    # ==============================================================

    renderer = GPURenderer(
        context,
        max_sprites=10000,
        max_shapes=10000,
        max_lines=10000,
        workers=4,

        # Important:
        # no font -> no text renderer
        font=None,
    )

    # ==========================================================
    # MODE
    # ==============================================================

    if MODE == 1:
        renderer.post_processor.enabled = False

        print()
        print(
            "Post-processing: DISABLED"
        )

        print(
            "Testing empty GPURenderer frames."
        )

    elif MODE == 2:
        renderer.post_processor.enabled = True

        print()
        print(
            "Post-processing: ENABLED"
        )

        print(
            "Testing empty GPURenderer frames "
            "through PostProcess."
        )

    else:
        raise ValueError(
            f"Unknown MODE: {MODE}"
        )

    print()

    print(
        "No sprites."
    )

    print(
        "No rectangles."
    )

    print(
        "No lines."
    )

    print(
        "No shapes."
    )

    print(
        "No text."
    )

    print()

    # ==========================================================
    # LOOP
    # ==============================================================

    frame_duration = (
        1.0
        / TARGET_FPS
    )

    running = True

    try:
        while running:
            frame_start = (
                time.perf_counter()
            )

            # ==================================================
            # EVENTS
            # ==================================================

            for event in context.poll_events():
                event_type = getattr(
                    event,
                    "type",
                    None,
                )

                if (
                    event_type
                    == sdl3.SDL_EVENT_QUIT
                ):
                    running = False
                    break

                if (
                    event_type
                    == sdl3.SDL_EVENT_WINDOW_CLOSE_REQUESTED
                ):
                    running = False
                    break

            if not running:
                break

            # ==================================================
            # RENDER
            # ==================================================

            if renderer.begin_frame():
                renderer.end_frame()

            # ==================================================
            # FPS LIMIT
            # ==================================================

            elapsed = (
                time.perf_counter()
                - frame_start
            )

            remaining = (
                frame_duration
                - elapsed
            )

            if remaining > 0.0:
                time.sleep(
                    remaining
                )

    finally:
        # ======================================================
        # SHUTDOWN
        # ======================================================

        try:
            renderer.destroy()

        finally:
            context.destroy()

        print()
        print(
            "Renderer + context destroyed."
        )


if __name__ == "__main__":
    main()