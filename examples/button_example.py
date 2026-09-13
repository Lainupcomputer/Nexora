from __future__ import annotations

import time
from ctypes import c_float
from pathlib import Path

import sdl3

from nexora.nodes import Button, Label
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.rendering.text import TextSystem
from nexora.scene import Scene
from nexora.ui import UIInput


ROOT = Path(__file__).resolve().parent.parent

FONT_PATH = (
    ROOT
    / "assets"
    / "fonts"
    / "Roboto-Regular.ttf"
)


def main() -> None:
    print("=" * 40)
    print(" Nexora Button / UI Test")
    print("=" * 40)
    print()

    if not FONT_PATH.is_file():
        raise FileNotFoundError(
            f"Font not found: {FONT_PATH}"
        )

    # --------------------------------------------------
    # Text system
    # --------------------------------------------------

    text_system = TextSystem()
    text_system.initialize()

    context = None
    font = None
    renderer = None

    try:
        # --------------------------------------------------
        # GPU context
        # --------------------------------------------------

        print("Creating GPU context...")

        context = GPUContext(
            1280,
            720,
            title="Nexora - Button UI Test",
            debug=True,
            vsync=True,
        )

        print(f"GPU driver: {context.driver}")
        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )
        print()

        # --------------------------------------------------
        # Font
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Renderer
        # --------------------------------------------------

        print("Creating Nexora renderer...")

        renderer = Renderer(
            context,
            font=font,
        )

        print()

        # --------------------------------------------------
        # Scene
        # --------------------------------------------------

        print("Creating scene...")

        scene = Scene("ButtonExample")

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # --------------------------------------------------
        # Title
        # --------------------------------------------------

        title = scene.ui.create_child(
            "Title",
            node_type=Label,
        )

        title.text = "Nexora Button Example"
        title.anchor = (0.5, 0.0)
        title.pivot = (0.5, 0.0)
        title.position = (0.0, 70.0)
        title.scale = 1.5

        # --------------------------------------------------
        # Button
        # --------------------------------------------------

        button = scene.ui.create_child(
            "TestButton",
            node_type=Button,
        )

        button.size = (
            300.0,
            80.0,
        )

        button.anchor = (0.5, 0.5)
        button.pivot = (0.5, 0.5)
        button.position = (
            0.0,
            0.0,
        )

        button.text = "Click me!"
        button.text_scale = 1.0

        # --------------------------------------------------
        # Button colors
        # --------------------------------------------------

        button.background_color = (
            0.15,
            0.15,
            0.20,
            1.0,
        )

        button.hover_background_color = (
            0.25,
            0.25,
            0.35,
            1.0,
        )

        button.pressed_background_color = (
            0.35,
            0.35,
            0.50,
            1.0,
        )

        # --------------------------------------------------
        # Click counter
        # --------------------------------------------------

        click_count = 0

        def on_click() -> None:
            nonlocal click_count

            click_count += 1

            print(
                f"Button clicked! "
                f"Count: {click_count}"
            )

        button.on_click = on_click

        # --------------------------------------------------
        # Status label
        # --------------------------------------------------

        status = scene.ui.create_child(
            "Status",
            node_type=Label,
        )

        status.text = "Waiting for input..."
        status.anchor = (0.5, 1.0)
        status.pivot = (0.5, 1.0)
        status.position = (
            0.0,
            -70.0,
        )

        # --------------------------------------------------
        # UI input
        # --------------------------------------------------

        ui_input = UIInput()

        # --------------------------------------------------
        # Mouse state
        # --------------------------------------------------

        previous_mouse_down = False

        # --------------------------------------------------
        # Main loop
        # --------------------------------------------------

        print("Rendering test scene...")
        print("Hover and click the button.")
        print("Close the window or press ESC to finish.")
        print()

        running = True

        while running:
            # --------------------------------------------------
            # Process events
            # --------------------------------------------------

            for event in context.poll_events():
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif event.type == sdl3.SDL_EVENT_KEY_DOWN:
                    if event.key.key == sdl3.SDLK_ESCAPE:
                        running = False

            if not running:
                break

            # --------------------------------------------------
            # Query current mouse state
            #
            # SDL coordinates:
            #     0,0 = top-left
            #
            # Nexora coordinates:
            #     0,0 = center
            # --------------------------------------------------

            mouse_x = c_float(0.0)
            mouse_y = c_float(0.0)

            mouse_buttons = sdl3.SDL_GetMouseState(
                mouse_x,
                mouse_y,
            )

            current_mouse_down = bool(
                mouse_buttons
                & sdl3.SDL_BUTTON_LMASK
            )

            # --------------------------------------------------
            # Mouse transitions
            # --------------------------------------------------

            mouse_pressed = (
                current_mouse_down
                and not previous_mouse_down
            )

            mouse_released = (
                not current_mouse_down
                and previous_mouse_down
            )

            previous_mouse_down = current_mouse_down

            # --------------------------------------------------
            # Convert coordinates
            # --------------------------------------------------

            ui_mouse_x = (
                float(mouse_x.value)
                - renderer.width / 2.0
            )

            ui_mouse_y = (
                float(mouse_y.value)
                - renderer.height / 2.0
            )

            # --------------------------------------------------
            # Update UI input
            # --------------------------------------------------

            ui_input.update_mouse(
                position=(
                    ui_mouse_x,
                    ui_mouse_y,
                ),
                down=current_mouse_down,
                pressed=mouse_pressed,
                released=mouse_released,
            )

            # --------------------------------------------------
            # Update UI
            # --------------------------------------------------

            scene.ui.update_input(
                ui_input,
            )

            # --------------------------------------------------
            # Status
            # --------------------------------------------------

            if button.pressed:
                status.text = "Pressed!"

            elif button.hovered:
                status.text = "Hovering..."

            else:
                status.text = (
                    f"Button clicked: "
                    f"{click_count}"
                )

            # --------------------------------------------------
            # Render
            # --------------------------------------------------

            if not renderer.begin_frame():
                time.sleep(0.001)
                continue

            try:
                scene.ui.render(
                    renderer,
                )

                if not renderer.end_frame():
                    break

            except Exception:
                context.cancel_frame()
                raise

            time.sleep(0.001)

    finally:
        print()
        print("Cleaning up...")

        if "scene" in locals() and scene is not None:
            scene.destroy()

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