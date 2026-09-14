from __future__ import annotations

import time
from pathlib import Path
from ctypes import c_float

import sdl3

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
        title="Nexora - CheckBox UI Test",
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

    scene = Scene("CheckBoxExample")

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

    title.text = "CheckBox Test"
    title.anchor = (0.5, 0.0)
    title.pivot = (0.5, 0.0)
    title.position = (0.0, 80.0)
    title.scale = 1.2

    # --------------------------------------------------
    # CheckBox 1
    # --------------------------------------------------

    checkbox_music = scene.ui.create_child(
        "Music",
        node_type=CheckBox,
    )

    checkbox_music.text = "Music"
    checkbox_music.anchor = (0.5, 0.5)
    checkbox_music.pivot = (0.5, 0.5)
    checkbox_music.position = (0.0, -40.0)

    # --------------------------------------------------
    # CheckBox 2
    # --------------------------------------------------

    checkbox_fullscreen = scene.ui.create_child(
        "Fullscreen",
        node_type=CheckBox,
    )

    checkbox_fullscreen.text = "Fullscreen"
    checkbox_fullscreen.anchor = (0.5, 0.5)
    checkbox_fullscreen.pivot = (0.5, 0.5)
    checkbox_fullscreen.position = (0.0, 40.0)

    # --------------------------------------------------
    # Status label
    # --------------------------------------------------

    status = scene.ui.create_child(
        "Status",
        node_type=Label,
    )

    status.anchor = (0.5, 1.0)
    status.pivot = (0.5, 1.0)
    status.position = (0.0, -80.0)

    def update_status() -> None:
        status.text = (
            f"Music: {'ON' if checkbox_music.checked else 'OFF'}   "
            f"Fullscreen: {'ON' if checkbox_fullscreen.checked else 'OFF'}"
        )

    def on_music_changed(checked: bool) -> None:
        update_status()
        print("Music:", checked)

    def on_fullscreen_changed(checked: bool) -> None:
        update_status()
        print("Fullscreen:", checked)

    checkbox_music.on_change = on_music_changed
    checkbox_fullscreen.on_change = on_fullscreen_changed

    update_status()

    running = True
    previous_mouse_down = False

    try:
        while running:
            for event in context.poll_events():
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif event.type == sdl3.SDL_EVENT_KEY_DOWN:
                    if event.key.key == sdl3.SDLK_ESCAPE:
                        running = False

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