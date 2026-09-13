from __future__ import annotations

import time
from ctypes import c_float
from pathlib import Path

import sdl3

from nexora.nodes import Label, Slider
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
    print(" Nexora Slider / UI Test")
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
            title="Nexora - Slider UI Test",
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

        scene = Scene("SliderExample")

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

        title.text = "Nexora Slider Example"
        title.anchor = (0.5, 0.0)
        title.pivot = (0.5, 0.0)
        title.position = (
            0.0,
            70.0,
        )
        title.scale = 1.5

        # ==================================================
        # Horizontal slider
        # ==================================================

        volume = scene.ui.create_child(
            "Volume",
            node_type=Slider,
        )

        volume.orientation = "horizontal"

        volume.length = 320.0
        volume.track_size = 8.0
        volume.handle_size = 28.0

        volume.min_value = 0.0
        volume.max_value = 100.0

        volume.set_value(
            50.0,
            emit=False,
        )

        volume.anchor = (
            0.5,
            0.5,
        )

        volume.pivot = (
            0.5,
            0.5,
        )

        volume.position = (
            -100.0,
            -100.0,
        )

        # --------------------------------------------------
        # Horizontal label
        # --------------------------------------------------

        volume_title = scene.ui.create_child(
            "VolumeTitle",
            node_type=Label,
        )

        volume_title.text = "Volume"
        volume_title.anchor = (
            0.5,
            0.5,
        )
        volume_title.pivot = (
            0.5,
            0.5,
        )
        volume_title.position = (
            -100.0,
            -150.0,
        )

        # --------------------------------------------------
        # Horizontal value
        # --------------------------------------------------

        volume_value = scene.ui.create_child(
            "VolumeValue",
            node_type=Label,
        )

        volume_value.text = "50"
        volume_value.anchor = (
            0.5,
            0.5,
        )
        volume_value.pivot = (
            0.5,
            0.5,
        )
        volume_value.position = (
            180.0,
            -100.0,
        )

        def on_volume_change(
            value: float,
        ) -> None:
            volume_value.text = (
                f"{value:.0f}"
            )

        volume.on_change = (
            on_volume_change
        )

        # ==================================================
        # Vertical slider
        # ==================================================

        brightness = scene.ui.create_child(
            "Brightness",
            node_type=Slider,
        )

        brightness.orientation = "vertical"

        brightness.length = 260.0
        brightness.track_size = 8.0
        brightness.handle_size = 28.0

        brightness.min_value = 0.0
        brightness.max_value = 100.0

        brightness.set_value(
            75.0,
            emit=False,
        )

        brightness.anchor = (
            0.5,
            0.5,
        )

        brightness.pivot = (
            0.5,
            0.5,
        )

        brightness.position = (
            300.0,
            0.0,
        )

        # --------------------------------------------------
        # Vertical label
        # --------------------------------------------------

        brightness_title = scene.ui.create_child(
            "BrightnessTitle",
            node_type=Label,
        )

        brightness_title.text = "Brightness"
        brightness_title.anchor = (
            0.5,
            0.5,
        )
        brightness_title.pivot = (
            0.5,
            0.5,
        )
        brightness_title.position = (
            300.0,
            170.0,
        )

        # --------------------------------------------------
        # Vertical value
        # --------------------------------------------------

        brightness_value = scene.ui.create_child(
            "BrightnessValue",
            node_type=Label,
        )

        brightness_value.text = "75"
        brightness_value.anchor = (
            0.5,
            0.5,
        )
        brightness_value.pivot = (
            0.5,
            0.5,
        )
        brightness_value.position = (
            350.0,
            0.0,
        )

        def on_brightness_change(
            value: float,
        ) -> None:
            brightness_value.text = (
                f"{value:.0f}"
            )

        brightness.on_change = (
            on_brightness_change
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
        print()
        print("Horizontal:")
        print("  Volume 0 - 100")
        print()
        print("Vertical:")
        print("  Brightness 0 - 100")
        print()
        print("Drag the sliders with the mouse.")
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

            previous_mouse_down = (
                current_mouse_down
            )

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