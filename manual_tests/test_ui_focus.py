from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.input.input import InputManager
from nexora.nodes import (
    Button,
    CheckBox,
    Dropdown,
    ListView,
    RadioButton,
    RadioButtonGroup,
    Slider,
    TextInput,
)
from nexora.rendering.renderer import Renderer
from nexora.rendering.gpu.context import GPUContext
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
    print(" Nexora UI Focus Test")
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
        # ------------------------------------------------------
        # GPU context
        # ------------------------------------------------------

        context = GPUContext(
            1280,
            900,
            title="Nexora - UI Focus Test",
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

        # ------------------------------------------------------
        # Font
        # ------------------------------------------------------

        font = text_system.font(
            FONT_PATH,
            32,
        )

        # ------------------------------------------------------
        # Renderer
        # ------------------------------------------------------

        renderer = Renderer(
            context,
            font=font,
        )

        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        input_manager = InputManager()

        input_manager.initialize(
            context.window,
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "UIFocusTest"
        )

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # ======================================================
        # Input A
        # ======================================================

        input_a = scene.ui.create_child(
            "InputA",
            node_type=TextInput,
        )

        input_a.anchor = (0.5, 0.5)
        input_a.pivot = (0.5, 0.5)

        input_a.position = (
            -260.0,
            -350.0,
        )

        input_a.placeholder = (
            "First input..."
        )

        # ======================================================
        # Input B
        # ======================================================

        input_b = scene.ui.create_child(
            "InputB",
            node_type=TextInput,
        )

        input_b.anchor = (0.5, 0.5)
        input_b.pivot = (0.5, 0.5)

        input_b.position = (
            260.0,
            -350.0,
        )

        input_b.placeholder = (
            "Second input..."
        )

        # ======================================================
        # Button
        # ======================================================

        button = scene.ui.create_child(
            "TestButton",
            node_type=Button,
        )

        button.text = "Click me"

        button.anchor = (0.5, 0.5)
        button.pivot = (0.5, 0.5)

        button.position = (
            -260.0,
            -260.0,
        )

        button.size = (
            300.0,
            60.0,
        )

        # ======================================================
        # Slider
        # ======================================================

        slider = scene.ui.create_child(
            "TestSlider",
            node_type=Slider,
        )

        slider.anchor = (0.5, 0.5)
        slider.pivot = (0.5, 0.5)

        slider.position = (
            260.0,
            -260.0,
        )

        slider.min_value = 0.0
        slider.max_value = 100.0
        slider.value = 50.0
        slider.step = 5.0

        slider.length = 400.0
        slider.track_size = 10.0
        slider.handle_size = 28.0

        # ======================================================
        # Dropdown
        # ======================================================

        dropdown = scene.ui.create_child(
            "TestDropdown",
            node_type=Dropdown,
        )

        dropdown.anchor = (0.5, 0.5)
        dropdown.pivot = (0.5, 0.5)

        dropdown.position = (
            -260.0,
            -170.0,
        )

        dropdown.size = (
            360.0,
            52.0,
        )

        dropdown.option_height = 42.0

        dropdown.set_options(
            [
                "Apple",
                "Banana",
                "Cherry",
                "Dragonfruit",
                "Elderberry",
            ]
        )

        dropdown.set_selected_index(
            1,
            emit=False,
        )

        # ======================================================
        # CheckBox
        # ======================================================

        checkbox = scene.ui.create_child(
            "TestCheckBox",
            node_type=CheckBox,
        )

        checkbox.anchor = (0.5, 0.5)
        checkbox.pivot = (0.5, 0.5)

        checkbox.position = (
            260.0,
            -170.0,
        )

        checkbox.size = (
            300.0,
            45.0,
        )

        checkbox.text = (
            "Enable feature"
        )

        checkbox.set_checked(
            False,
            emit=False,
        )

        # ======================================================
        # Radio Button Group
        # ======================================================

        radio_group = RadioButtonGroup()

        radio_a = scene.ui.create_child(
            "RadioA",
            node_type=RadioButton,
        )

        radio_a.anchor = (0.5, 0.5)
        radio_a.pivot = (0.5, 0.5)

        radio_a.position = (
            -240.0,
            -60.0,
        )

        radio_a.text = "Option A"
        radio_a.set_group(radio_group)

        radio_b = scene.ui.create_child(
            "RadioB",
            node_type=RadioButton,
        )

        radio_b.anchor = (0.5, 0.5)
        radio_b.pivot = (0.5, 0.5)

        radio_b.position = (
            0.0,
            -60.0,
        )

        radio_b.text = "Option B"
        radio_b.set_group(radio_group)

        radio_c = scene.ui.create_child(
            "RadioC",
            node_type=RadioButton,
        )

        radio_c.anchor = (0.5, 0.5)
        radio_c.pivot = (0.5, 0.5)

        radio_c.position = (
            240.0,
            -60.0,
        )

        radio_c.text = "Option C"
        radio_c.set_group(radio_group)

        radio_a.set_selected(
            True,
            emit=False,
        )

        # ======================================================
        # ListView
        # ======================================================

        list_view = scene.ui.create_child(
            "TestListView",
            node_type=ListView,
        )

        list_view.anchor = (
            0.5,
            0.5,
        )

        list_view.pivot = (
            0.5,
            0.5,
        )

        list_view.position = (
            0.0,
            220.0,
        )

        list_view.size = (
            500.0,
            280.0,
        )

        list_view.item_height = 42.0
        list_view.spacing = 4.0

        list_view.set_items(
            [
                f"List Item {i}"
                for i in range(1, 21)
            ]
        )

        list_view.set_selected_index(
            0,
            emit=False,
        )

        # ======================================================
        # Callbacks
        # ======================================================

        input_a.on_change = lambda text: print(
            f"[InputA] text = {text!r}"
        )

        input_b.on_change = lambda text: print(
            f"[InputB] text = {text!r}"
        )

        input_a.on_submit = lambda text: print(
            f"[InputA] submit = {text!r}"
        )

        input_b.on_submit = lambda text: print(
            f"[InputB] submit = {text!r}"
        )

        button.on_click = lambda: print(
            "[Button] CLICK!"
        )

        slider.on_change = lambda value: print(
            f"[Slider] value = {value:.2f}"
        )

        dropdown.on_change = lambda index, value: print(
            f"[Dropdown] index = {index}, "
            f"value = {value!r}"
        )

        checkbox.on_change = lambda checked: print(
            f"[CheckBox] checked = {checked}"
        )

        radio_a.on_change = lambda selected: print(
            f"[RadioA] selected = {selected}"
        )

        radio_b.on_change = lambda selected: print(
            f"[RadioB] selected = {selected}"
        )

        radio_c.on_change = lambda selected: print(
            f"[RadioC] selected = {selected}"
        )

        list_view.on_change = lambda index, value: print(
            f"[ListView] selected = "
            f"{index}, {value!r}"
        )

        list_view.on_activate = lambda index, value: print(
            f"[ListView] activated = "
            f"{index}, {value!r}"
        )

        # ======================================================
        # Instructions
        # ======================================================

        print("Test:")
        print()

        print("Focus navigation:")
        print("  TAB        -> next control")
        print("  SHIFT+TAB  -> previous control")
        print()

        print("Expected focus order:")
        print()
        print("  InputA")
        print("    -> InputB")
        print("    -> TestButton")
        print("    -> TestSlider")
        print("    -> TestDropdown")
        print("    -> TestCheckBox")
        print("    -> RadioA")
        print("    -> RadioB")
        print("    -> RadioC")
        print("    -> TestListView")
        print("    -> InputA")
        print()

        print("Button:")
        print("  ENTER / SPACE -> click")
        print()

        print("Slider:")
        print("  LEFT / DOWN   -> -5")
        print("  RIGHT / UP    -> +5")
        print("  HOME          -> 0")
        print("  END           -> 100")
        print()

        print("Dropdown:")
        print("  ENTER / SPACE -> open/select")
        print("  UP / DOWN     -> move highlight")
        print("  HOME          -> first option")
        print("  END           -> last option")
        print("  ESC           -> close")
        print()

        print("CheckBox:")
        print("  SPACE / ENTER -> toggle")
        print()

        print("RadioButtons:")
        print("  SPACE / ENTER -> select")
        print("  LEFT / UP     -> previous radio")
        print("  RIGHT / DOWN  -> next radio")
        print()

        print("ListView:")
        print("  UP / DOWN       -> move selection")
        print("  HOME / END      -> first / last")
        print("  PAGEUP          -> page up")
        print("  PAGEDOWN        -> page down")
        print("  ENTER / SPACE   -> activate")
        print("  Mouse wheel     -> scroll")
        print("  Mouse click     -> select item")
        print()

        print("Mouse:")
        print("  Every control should also work by mouse")
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
                        if not dropdown.opened:
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

            # --------------------------------------------------
            # SDL -> Nexora mouse coordinates
            # --------------------------------------------------

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

            # --------------------------------------------------
            # UI mouse
            # --------------------------------------------------

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

            # --------------------------------------------------
            # UI keyboard
            # --------------------------------------------------

            scene.ui_input.update_keyboard(
                keys_down=input_manager.keys_down,
                keys_pressed=input_manager.keys_pressed,
                keys_released=input_manager.keys_released,
            )

            # --------------------------------------------------
            # Text
            # --------------------------------------------------

            scene.ui_input.update_text_input(
                input_manager.text_input,
            )

            # --------------------------------------------------
            # UI update
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
            # Text input mode
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