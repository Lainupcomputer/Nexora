from __future__ import annotations

import sdl3


def show(name, value):
    print(f"{name:<45} {value!r}")


print("=" * 70)
print(" Nexora SDL3 Resize API Test")
print("=" * 70)
print()

print("SDL version:")
try:
    version = sdl3.SDL_GetVersion()
    show("SDL_GetVersion()", version)
except Exception as exc:
    print("SDL_GetVersion() failed:", repr(exc))

print()
print("Window flags:")

show(
    "SDL_WINDOW_RESIZABLE",
    getattr(sdl3, "SDL_WINDOW_RESIZABLE", "<missing>"),
)

show(
    "SDL_WINDOW_RESIZABLE type",
    type(getattr(sdl3, "SDL_WINDOW_RESIZABLE", None)),
)

print()
print("Resize event constants:")

for name in (
    "SDL_EVENT_WINDOW_RESIZED",
    "SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED",
    "SDL_EVENT_WINDOW_RESIZING",
    "SDL_EVENT_WINDOW_SIZE_CHANGED",
):
    show(
        name,
        getattr(sdl3, name, "<missing>"),
    )

print()
print("Window event type:")

try:
    show(
        "SDL_WindowEvent",
        getattr(sdl3, "SDL_WindowEvent", "<missing>"),
    )

    show(
        "SDL_WindowEvent type",
        type(getattr(sdl3, "SDL_WindowEvent", None)),
    )

except Exception as exc:
    print(
        "SDL_WindowEvent inspection failed:",
        repr(exc),
    )

print()
print("SDL_Event:")

try:
    event = sdl3.SDL_Event()

    show(
        "SDL_Event",
        event,
    )

    show(
        "SDL_Event type",
        type(event),
    )

    print()
    print("SDL_Event fields:")

    try:
        for field in event._fields_:
            print("  ", field)
    except Exception as exc:
        print(
            "  Could not inspect _fields_:",
            repr(exc),
        )

except Exception as exc:
    print(
        "SDL_Event inspection failed:",
        repr(exc),
    )

print()
print("Window functions:")

for name in (
    "SDL_CreateWindow",
    "SDL_SetWindowSize",
    "SDL_GetWindowSize",
    "SDL_GetWindowSizeInPixels",
    "SDL_GetWindowFlags",
):
    show(
        name,
        getattr(sdl3, name, "<missing>"),
    )

print()
print("=" * 70)
print(" SDL3 API inspection finished")
print("=" * 70)
print()
print(
    "No window was created and no SDL subsystem "
    "was initialized."
)