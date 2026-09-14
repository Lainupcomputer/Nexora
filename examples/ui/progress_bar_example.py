from __future__ import annotations

import time
from ctypes import c_float
from pathlib import Path

import sdl3

from nexora.nodes import Label, ProgressBar
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
    print(" Nexora ProgressBar / UI Test")
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
            title="Nexora - ProgressBar UI Test",
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

        scene = Scene("ProgressBarExample")

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

        title.text = "Nexora ProgressBar Example"
        title.anchor = (0.5, 0.0)
        title.pivot = (0.5, 0.0)
        title.position = (
            0.0,
            70.0,
        )
        title.scale = 1.5

        # ==================================================
        # Horizontal Health Bar
        # ==================================================

        health = scene.ui.create_child(
            "Health",
            node_type=ProgressBar,
        )

        health.orientation = "horizontal"

        health.length = 360.0
        health.thickness = 28.0

        health.min_value = 0.0
        health.max_value = 100.0
        health.set_value(75.0)

        health.anchor = (
            0.5,
            0.5,
        )

        health.pivot = (
            0.5,
            0.5,
        )

        health.position = (
            -100.0,
            -80.0,
        )

        # --------------------------------------------------
        # Health colors
        # --------------------------------------------------

        health.background = (
            32,
            34,
            37,
            255,
        )

        health.fill_color = (
            45,
            160,
            75,
            255,
        )

        health.border_color = (
            80,
            80,
            85,
            255,
        )

        health.border_width = 2.0
        health.border_radius = 8.0

        # --------------------------------------------------
        # Health title
        # --------------------------------------------------

        health_title = scene.ui.create_child(
            "HealthTitle",
            node_type=Label,
        )

        health_title.text = "Health"
        health_title.anchor = (
            0.5,
            0.5,
        )
        health_title.pivot = (
            0.5,
            0.5,
        )
        health_title.position = (
            -100.0,
            -125.0,
        )

        # --------------------------------------------------
        # Health value
        # --------------------------------------------------

        health_value = scene.ui.create_child(
            "HealthValue",
            node_type=Label,
        )

        health_value.text = "75 / 100"
        health_value.anchor = (
            0.5,
            0.5,
        )
        health_value.pivot = (
            0.5,
            0.5,
        )
        health_value.position = (
            -100.0,
            -35.0,
        )

        # ==================================================
        # Vertical XP Bar
        # ==================================================

        xp = scene.ui.create_child(
            "XP",
            node_type=ProgressBar,
        )

        xp.orientation = "vertical"

        xp.length = 280.0
        xp.thickness = 28.0

        xp.min_value = 0.0
        xp.max_value = 100.0
        xp.set_value(40.0)

        xp.anchor = (
            0.5,
            0.5,
        )

        xp.pivot = (
            0.5,
            0.5,
        )

        xp.position = (
            300.0,
            0.0,
        )

        # --------------------------------------------------
        # XP colors
        # --------------------------------------------------

        xp.background = (
            32,
            34,
            37,
            255,
        )

        xp.fill_color = (
            70,
            110,
            200,
            255,
        )

        xp.border_color = (
            80,
            80,
            85,
            255,
        )

        xp.border_width = 2.0
        xp.border_radius = 8.0

        # --------------------------------------------------
        # XP title
        # --------------------------------------------------

        xp_title = scene.ui.create_child(
            "XPTitle",
            node_type=Label,
        )

        xp_title.text = "XP"
        xp_title.anchor = (
            0.5,
            0.5,
        )
        xp_title.pivot = (
            0.5,
            0.5,
        )
        xp_title.position = (
            300.0,
            170.0,
        )

        # --------------------------------------------------
        # XP value
        # --------------------------------------------------

        xp_value = scene.ui.create_child(
            "XPValue",
            node_type=Label,
        )

        xp_value.text = "40 / 100"
        xp_value.anchor = (
            0.5,
            0.5,
        )
        xp_value.pivot = (
            0.5,
            0.5,
        )
        xp_value.position = (
            360.0,
            0.0,
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
        print("  Health: 75 / 100")
        print()
        print("Vertical:")
        print("  XP: 40 / 100")
        print()
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