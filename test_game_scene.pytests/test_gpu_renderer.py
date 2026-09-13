from __future__ import annotations

import time

import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.renderer import GPURenderer


print("=" * 40)
print(" Nexora GPU Renderer Resize Test")
print("=" * 40)
print()

context = GPUContext(
    1280,
    720,
    title="Nexora Resize Renderer Test",
    resizable=True,
)

renderer = GPURenderer(
    context,
)

print("GPU context ready.")
print(f"GPU driver: {renderer.driver}")
print()

running = True
frames = 0

try:
    while running:

        # ----------------------------------------------------------
        # SDL Events
        # ----------------------------------------------------------

        for event in context.poll_events():

            if event.type == sdl3.SDL_EVENT_QUIT:
                running = False
                break

            if event.type == sdl3.SDL_EVENT_WINDOW_RESIZED:
                print(
                    "WINDOW_RESIZED:",
                    event.window.data1,
                    "x",
                    event.window.data2,
                )

            elif (
                event.type
                == sdl3.SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED
            ):
                print(
                    "PIXEL_SIZE_CHANGED:",
                    event.window.data1,
                    "x",
                    event.window.data2,
                )

        if not running:
            break

        # ----------------------------------------------------------
        # Begin frame
        # ----------------------------------------------------------

        if not renderer.begin_frame():
            time.sleep(0.01)
            continue

        try:
            width = renderer.width
            height = renderer.height

            # ------------------------------------------------------
            # Crosshair at world origin
            # ------------------------------------------------------

            renderer.line(
                -100,
                0,
                100,
                0,
                width=2.0,
                color=(1.0, 0.2, 0.2, 1.0),
            )

            renderer.line(
                0,
                -100,
                0,
                100,
                width=2.0,
                color=(0.2, 1.0, 0.2, 1.0),
            )

            # ------------------------------------------------------
            # Center rectangle
            # ------------------------------------------------------

            renderer.rect(
                0,
                0,
                100,
                100,
                color=(0.2, 0.6, 1.0, 1.0),
                rotation=0.0,
            )

            # ------------------------------------------------------
            # Screen-edge reference
            # ------------------------------------------------------

            half_width = width * 0.5
            half_height = height * 0.5

            renderer.line(
                -half_width,
                -half_height,
                half_width,
                -half_height,
                width=2.0,
                color=(1.0, 1.0, 1.0, 1.0),
            )

            renderer.line(
                half_width,
                -half_height,
                half_width,
                half_height,
                width=2.0,
                color=(1.0, 1.0, 1.0, 1.0),
            )

            renderer.line(
                half_width,
                half_height,
                -half_width,
                half_height,
                width=2.0,
                color=(1.0, 1.0, 1.0, 1.0),
            )

            renderer.line(
                -half_width,
                half_height,
                -half_width,
                -half_height,
                width=2.0,
                color=(1.0, 1.0, 1.0, 1.0),
            )

        finally:
            renderer.end_frame()

        frames += 1

        if frames % 60 == 0:
            print(
                f"Frame {frames}: "
                f"{renderer.width}x{renderer.height}"
            )

        time.sleep(1.0 / 60.0)

finally:
    renderer.destroy()
    context.destroy()

print()
print("Resize renderer test finished.")