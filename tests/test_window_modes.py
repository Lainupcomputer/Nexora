from __future__ import annotations

import time

import sdl3

from nexora.rendering.gpu.context import (
    GPUContext,
    WindowMode,
)


print("=" * 40)
print(" Nexora Window Mode Test")
print("=" * 40)
print()

context = GPUContext(
    1280,
    720,
    title="Nexora Window Mode Test",
    resizable=True,
    vsync=True,
)

print("GPU driver:", context.driver)
print("Initial mode:", context.window_mode.value)
print("VSync:", context.vsync)
print()

print("Controls:")
print("  1 = Windowed")
print("  2 = Borderless")
print("  3 = Fullscreen")
print("  V = Toggle VSync")
print("  ESC / close = Exit")
print()

try:
    running = True

    while running:

        for event in context.poll_events():

            if event.type == sdl3.SDL_EVENT_QUIT:
                running = False
                break

            if (
                event.type
                == sdl3.SDL_EVENT_KEY_DOWN
            ):
                key = event.key.key

                # SDL_SCANCODE_1
                if key == sdl3.SDLK_1:
                    context.set_windowed()
                    print(
                        "Mode:",
                        context.window_mode.value,
                    )

                # SDL_SCANCODE_2
                elif key == sdl3.SDLK_2:
                    context.set_borderless()
                    print(
                        "Mode:",
                        context.window_mode.value,
                    )

                # SDL_SCANCODE_3
                elif key == sdl3.SDLK_3:
                    context.set_fullscreen()
                    print(
                        "Mode:",
                        context.window_mode.value,
                    )

                # V
                elif key == sdl3.SDLK_V:
                    context.set_vsync(
                        not context.vsync
                    )

                    print(
                        "VSync:",
                        context.vsync,
                    )

                # ESC
                elif key == sdl3.SDLK_ESCAPE:
                    running = False
                    break

        time.sleep(0.01)

finally:
    context.destroy()

print()
print("Window mode test finished.")