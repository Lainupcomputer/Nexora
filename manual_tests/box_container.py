from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.input.input import InputManager
from nexora.nodes import (
    Button,
    CheckBox,
    HBoxContainer,
    Slider,
    TextInput,
    VBoxContainer,
)
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.rendering.text import TextSystem
from nexora.scene import Scene
from nexora.threading.context import ThreadContext


ROOT = Path(__file__).resolve().parent.parent

FONT_PATH = (
    ROOT
    / "assets"
    / "fonts"
    / "Roboto-Regular.ttf"
)


def main() -> None:
    print("=" * 50)
    print(" Nexora BoxContainer Test")
    print("=" * 50)
    print()

    if not FONT_PATH.is_file():
        raise FileNotFoundError(
            f"Font not found: {FONT_PATH}"
        )

    ThreadContext.initialize()

    text_system = TextSystem()
    text_system.initialize()

    context = None
    font = None
    renderer = None
    input_manager = None
    scene = None

    try:
        # ======================================================
        # GPU
        # ======================================================

        context = GPUContext(
            1280,
            800,
            title="Nexora - BoxContainer Test",
            debug=True,
            vsync=True,
            resizable=True,
        )

        print(
            f"GPU driver: {context.driver}"
        )

        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )

        print()

        # ======================================================
        # Font
        # ======================================================

        font = text_system.font(
            FONT_PATH,
            32,
        )

        # ======================================================
        # Renderer
        # ======================================================

        renderer = Renderer(
            context,
            font=font,
        )

        # ======================================================
        # Input
        # ======================================================

        input_manager = InputManager()

        input_manager.initialize(
            context.window,
        )

        # ======================================================
        # Scene
        # ======================================================

        scene = Scene(
            "BoxContainerTest"
        )

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # ======================================================
        # VBox
        # ======================================================

        vbox = scene.ui.create_child(
            "VBox",
            node_type=VBoxContainer,
        )

        vbox.anchor = (
            0.5,
            0.5,
        )

        vbox.pivot = (
            0.5,
            0.5,
        )

        vbox.position = (
            -280.0,
            0.0,
        )

        vbox.size = (
            420.0,
            520.0,
        )

        vbox.spacing = 18.0

        vbox.padding_left = 20.0
        vbox.padding_top = 20.0
        vbox.padding_right = 20.0
        vbox.padding_bottom = 20.0

        vbox.alignment = "center"

        # ------------------------------------------------------
        # VBox TextInput
        # ------------------------------------------------------

        text_input = vbox.create_child(
            "VBoxInput",
            node_type=TextInput,
        )

        text_input.placeholder = (
            "Enter name..."
        )

        # ------------------------------------------------------
        # VBox Button 1
        # ------------------------------------------------------

        play_button = vbox.create_child(
            "PlayButton",
            node_type=Button,
        )

        play_button.text = "Play"

        play_button.size = (
            300.0,
            60.0,
        )

        # ------------------------------------------------------
        # VBox Button 2
        # ------------------------------------------------------

        settings_button = vbox.create_child(
            "SettingsButton",
            node_type=Button,
        )

        settings_button.text = "Settings"

        settings_button.size = (
            300.0,
            60.0,
        )

        # ------------------------------------------------------
        # VBox Checkbox
        # ------------------------------------------------------

        checkbox = vbox.create_child(
            "FullscreenCheckBox",
            node_type=CheckBox,
        )

        checkbox.text = (
            "Fullscreen"
        )

        checkbox.size = (
            300.0,
            45.0,
        )

        # ------------------------------------------------------
        # VBox Slider
        # ------------------------------------------------------

        slider = vbox.create_child(
            "VolumeSlider",
            node_type=Slider,
        )

        slider.min_value = 0.0
        slider.max_value = 100.0
        slider.value = 50.0
        slider.step = 5.0

        slider.length = 300.0
        slider.track_size = 10.0
        slider.handle_size = 28.0

        # ======================================================
        # HBox
        # ======================================================

        hbox = scene.ui.create_child(
            "HBox",
            node_type=HBoxContainer,
        )

        hbox.anchor = (
            0.5,
            0.5,
        )

        hbox.pivot = (
            0.5,
            0.5,
        )

        hbox.position = (
            300.0,
            0.0,
        )

        hbox.size = (
            520.0,
            180.0,
        )

        hbox.spacing = 15.0

        hbox.padding_left = 20.0
        hbox.padding_top = 20.0
        hbox.padding_right = 20.0
        hbox.padding_bottom = 20.0

        hbox.alignment = "center"

        # ------------------------------------------------------
        # HBox buttons
        # ------------------------------------------------------

        yes_button = hbox.create_child(
            "YesButton",
            node_type=Button,
        )

        yes_button.text = "Yes"

        yes_button.size = (
            140.0,
            60.0,
        )

        no_button = hbox.create_child(
            "NoButton",
            node_type=Button,
        )

        no_button.text = "No"

        no_button.size = (
            140.0,
            60.0,
        )

        maybe_button = hbox.create_child(
            "MaybeButton",
            node_type=Button,
        )

        maybe_button.text = "Maybe"

        maybe_button.size = (
            140.0,
            60.0,
        )

        # ======================================================
        # Callbacks
        # ======================================================

        play_button.on_click = lambda: print(
            "[VBox] Play clicked"
        )

        settings_button.on_click = lambda: print(
            "[VBox] Settings clicked"
        )

        checkbox.on_change = lambda checked: print(
            f"[VBox] Fullscreen = {checked}"
        )

        slider.on_change = lambda value: print(
            f"[VBox] Volume = {value:.1f}"
        )

        yes_button.on_click = lambda: print(
            "[HBox] Yes clicked"
        )

        no_button.on_click = lambda: print(
            "[HBox] No clicked"
        )

        maybe_button.on_click = lambda: print(
            "[HBox] Maybe clicked"
        )

        # ======================================================
        # Instructions
        # ======================================================

        print("Test:")
        print()
        print("Left side:")
        print("  VBoxContainer")
        print("  Elements should be stacked vertically")
        print("  and centered horizontally.")
        print()
        print("Right side:")
        print("  HBoxContainer")
        print("  Buttons should be laid out horizontally")
        print("  and centered vertically.")
        print()
        print("Keyboard:")
        print("  TAB / SHIFT+TAB -> focus navigation")
        print("  ENTER / SPACE   -> buttons")
        print("  SPACE           -> checkbox")
        print("  Arrow keys      -> slider")
        print()
        print("ESC closes the test.")
        print()

        # ======================================================
        # Loop
        # ======================================================

        running = True
        last_focus = None

        while running:
            # --------------------------------------------------
            # Events
            # --------------------------------------------------

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

                elif (
                    event.type
                    == sdl3.SDL_EVENT_WINDOW_RESIZED
                ):
                    scene.ui.set_viewport_size(
                        renderer.width,
                        renderer.height,
                    )

            if not running:
                break

            # --------------------------------------------------
            # Input
            # --------------------------------------------------

            input_manager.begin_frame(
                events,
            )

            mouse_x, mouse_y = (
                input_manager.mouse_position
            )

            ui_mouse_x = (
                mouse_x
                - renderer.width / 2.0
            )

            ui_mouse_y = (
                mouse_y
                - renderer.height / 2.0
            )

            wheel_x, wheel_y = (
                input_manager.wheel
            )

            scene.ui_input.update_mouse(
                position=(
                    ui_mouse_x,
                    ui_mouse_y,
                ),
                down=input_manager.mouse_down(
                    "left",
                ),
                pressed=input_manager.mouse_pressed(
                    "left",
                ),
                released=input_manager.mouse_released(
                    "left",
                ),
                wheel_x=wheel_x,
                wheel_y=wheel_y,
            )

            scene.ui_input.update_keyboard(
                keys_down=input_manager.keys_down,
                keys_pressed=input_manager.keys_pressed,
                keys_released=input_manager.keys_released,
            )

            scene.ui_input.update_text_input(
                input_manager.text_input,
            )

            # --------------------------------------------------
            # Update UI
            # --------------------------------------------------

            scene.ui.update_input(
                scene.ui_input,
            )

            # --------------------------------------------------
            # Focus debug
            # --------------------------------------------------

            current_focus = (
                scene.ui.focused_node
            )

            if current_focus is not last_focus:
                if current_focus is None:
                    print(
                        "[Focus] None"
                    )

                else:
                    print(
                        f"[Focus] "
                        f"{current_focus.name}"
                    )

                last_focus = current_focus

            # --------------------------------------------------
            # SDL text input
            # --------------------------------------------------

            if isinstance(
                scene.ui.focused_node,
                TextInput,
            ):
                input_manager.start_text_input()

            else:
                input_manager.stop_text_input()

            # --------------------------------------------------
            # Render
            # --------------------------------------------------

            if not renderer.begin_frame():
                input_manager.end_frame()

                time.sleep(
                    0.001
                )

                continue

            try:
                scene.ui.render(
                    renderer
                )

                if not renderer.end_frame():
                    break

            except Exception:
                context.cancel_frame()
                raise

            input_manager.end_frame()

            time.sleep(
                0.001
            )

    finally:
        print()
        print("Cleaning up...")

        if input_manager is not None:
            input_manager.stop_text_input()

        if scene is not None:
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