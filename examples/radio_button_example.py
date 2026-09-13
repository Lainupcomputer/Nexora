from __future__ import annotations

import time
from ctypes import c_float
from pathlib import Path

import sdl3

from nexora.nodes import Label, RadioButton, RadioButtonGroup
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.rendering.text import TextSystem
from nexora.scene import Scene

from nexora.nodes import CheckBox, Label
from nexora.rendering.renderer import Renderer
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.text import TextSystem
from nexora.scene import Scene
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.rendering.text import TextSystem
from nexora.scene import Scene
from nexora.ui import UIInput


ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "Roboto-Regular.ttf"


def main() -> None:
    text_system = TextSystem()
    text_system.initialize()

    context = GPUContext(
        1280,
        720,
        title="Nexora - RadioButton UI Test",
        debug=True,
        vsync=True,
    )

    font = text_system.font(
        FONT_PATH,
        32,
    )

    renderer = Renderer(
        context,
        font=font,
    )

    scene = Scene("RadioButtonExample")

    scene.ui.set_viewport_size(
        renderer.width,
        renderer.height,
    )

    ui_input = UIInput()

    # --------------------------------------------------
    # Title
    # --------------------------------------------------

    title = scene.ui.create_child(
        "Title",
        node_type=Label,
    )

    title.text = "RadioButton Test"
    title.anchor = (0.5, 0.0)
    title.pivot = (0.5, 0.0)
    title.position = (0.0, 80.0)
    title.scale = 1.2

    # --------------------------------------------------
    # Radio button group
    # --------------------------------------------------

    group = RadioButtonGroup()

    # --------------------------------------------------
    # Radio button 1
    # --------------------------------------------------

    option_a = scene.ui.create_child(
        "OptionA",
        node_type=RadioButton,
    )

    option_a.text = "Option A"
    option_a.anchor = (0.5, 0.5)
    option_a.pivot = (0.5, 0.5)
    option_a.position = (0.0, -80.0)
    option_a.set_group(group)

    # --------------------------------------------------
    # Radio button 2
    # --------------------------------------------------

    option_b = scene.ui.create_child(
        "OptionB",
        node_type=RadioButton,
    )

    option_b.text = "Option B"
    option_b.anchor = (0.5, 0.5)
    option_b.pivot = (0.5, 0.5)
    option_b.position = (0.0, 0.0)
    option_b.set_group(group)

    # --------------------------------------------------
    # Radio button 3
    # --------------------------------------------------

    option_c = scene.ui.create_child(
        "OptionC",
        node_type=RadioButton,
    )

    option_c.text = "Option C"
    option_c.anchor = (0.5, 0.5)
    option_c.pivot = (0.5, 0.5)
    option_c.position = (0.0, 80.0)
    option_c.set_group(group)

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    status = scene.ui.create_child(
        "Status",
        node_type=Label,
    )

    status.anchor = (0.5, 1.0)
    status.pivot = (0.5, 1.0)
    status.position = (0.0, -80.0)

    def update_status() -> None:
        selected = group.selected

        if selected is None:
            status.text = "Selected: None"
        else:
            status.text = f"Selected: {selected.text}"

    def on_change(checked: bool) -> None:
        update_status()
        print(
            "Selected:",
            group.selected.text
            if group.selected is not None
            else "None",
        )

    option_a.on_change = on_change
    option_b.on_change = on_change
    option_c.on_change = on_change

    # Start with Option A selected.
    option_a.set_selected(True)

    update_status()

    # --------------------------------------------------
    # Main loop
    # --------------------------------------------------

    running = True
    previous_mouse_down = False

    try:
        while running:
            # --------------------------------------------------
            # Events
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
            # Mouse state
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

            mouse_pressed = (
                current_mouse_down
                and not previous_mouse_down
            )

            mouse_released = (
                not current_mouse_down
                and previous_mouse_down
            )

            previous_mouse_down = current_mouse_down

            ui_mouse_x = (
                float(mouse_x.value)
                - renderer.width / 2.0
            )

            ui_mouse_y = (
                float(mouse_y.value)
                - renderer.height / 2.0
            )

            ui_input.update_mouse(
                position=(
                    ui_mouse_x,
                    ui_mouse_y,
                ),
                down=current_mouse_down,
                pressed=mouse_pressed,
                released=mouse_released,
            )

            scene.ui.update_input(ui_input)

            # --------------------------------------------------
            # Render
            # --------------------------------------------------

            renderer.begin_frame()

            scene.ui.render(renderer)

            renderer.end_frame()

            time.sleep(0.001)

    finally:
        scene.destroy()
        renderer.destroy()
        font.close()
        context.destroy()
        text_system.shutdown()


if __name__ == "__main__":
    main()