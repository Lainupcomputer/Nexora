from __future__ import annotations

import time

import sdl3

from nexora.rendering.gpu.context import GPUContext


print("=" * 40)
print(" Nexora GPU Resize Test")
print("=" * 40)
print()

context = GPUContext(
    1280,
    720,
    title="Nexora Resize Test",
    resizable=True,
)

print("GPU context ready.")
print(f"Resizable: {context.resizable}")
print(f"Initial size: {context.width}x{context.height}")
print()

try:
    print("Resize the window manually.")
    print("The current size will be printed whenever SDL")
    print("reports a resize event.")
    print()
    print("Press the window close button to finish.")
    print()

    running = True

    while running:
        for event in context.poll_events():
            if event.type == 0x100:
                running = False
                break

            if event.type == sdl3.SDL_EVENT_WINDOW_RESIZED:
                print(
                    "WINDOW_RESIZED:",
                    event.window.data1,
                    "x",
                    event.window.data2,
                )

            elif event.type == sdl3.SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED:
                print(
                    "PIXEL_SIZE_CHANGED:",
                    event.window.data1,
                    "x",
                    event.window.data2,
                )

        time.sleep(0.01)

finally:
    context.destroy()

print()
print("Resize test finished.")