from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.input.input import InputManager
from nexora.nodes import TextInput
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
    print("=" * 40)
    print(" Nexora TextInput UI Test")
    print("=" * 40)
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
        print("Creating GPU context...")

        context = GPUContext(
            1280,
            720,
            title="Nexora - TextInput UI Test",
            debug=True,
            vsync=True,
        )

        print(f"GPU driver: {context.driver}")
        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )
        print()

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

        print("Creating Nexora renderer...")

        renderer = Renderer(
            context,
            font=font,
        )

        print()

        print("Creating input manager...")

        input_manager = InputManager()
        input_manager.initialize(
            context.window,
        )

        print()

        print("Creating scene...")

        scene = Scene("TextInputExample")

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # --------------------------------------------------
        # TextInput
        # --------------------------------------------------

        text_input = scene.ui.create_child(
            "TextInput",
            node_type=TextInput,
        )

        text_input.anchor = (
            0.5,
            0.5,
        )

        text_input.pivot = (
            0.5,
            0.5,
        )

        text_input.position = (
            0.0,
            0.0,
        )

        text_input.size = (
            500.0,
            60.0,
        )

        text_input.placeholder = (
            "Enter text..."
        )

        text_input.max_length = 100

        # --------------------------------------------------
        # Callbacks
        # --------------------------------------------------

        def on_change(text: str) -> None:
            print(
                f"Text changed: {text!r}"
            )

        def on_submit(text: str) -> None:
            print(
                f"Submitted: {text!r}"
            )

        text_input.on_change = on_change
        text_input.on_submit = on_submit

        # --------------------------------------------------
        # Information labels
        # --------------------------------------------------

        info = scene.ui.create_child(
            "Info",
        )

        info.anchor = (
            0.5,
            0.0,
        )

        info.pivot = (
            0.5,
            0.0,
        )

        info.position = (
            0.0,
            40.0,
        )

        # The TextInput example intentionally keeps the
        # actual input field as the main UI element.
        # Additional debug output is printed to the console.

        print("TextInput:")
        print(
            "  Click the field to focus it."
        )
        print(
            "  Type text."
        )
        print(
            "  Backspace / Delete."
        )
        print(
            "  Left / Right."
        )
        print(
            "  Home / End."
        )
        print(
            "  Enter to submit."
        )
        print(
            "  Click outside to remove focus."
        )
        print()
        print(
            "Close the window or press ESC to finish."
        )
        print()

        running = True

        while running:
            # --------------------------------------------------
            # SDL events
            # --------------------------------------------------

            events = list(
                context.poll_events()
            )

            for event in events:
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif event.type == sdl3.SDL_EVENT_KEY_DOWN:
                    if event.key.key == sdl3.SDLK_ESCAPE:
                        running = False

            if not running:
                break

            # --------------------------------------------------
            # InputManager
            # --------------------------------------------------

            input_manager.begin_frame(
                events,
            )

            # --------------------------------------------------
            # Convert SDL coordinates to Nexora UI coordinates
            #
            # SDL:
            #   (0, 0) = top-left
            #
            # Nexora UI:
            #   (0, 0) = center
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

            # --------------------------------------------------
            # Update UIInput
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
            )

            scene.ui_input.update_keyboard(
                keys_down=input_manager.keys_down,
                keys_pressed=input_manager.keys_pressed,
                keys_released=input_manager.keys_released,
            )

            scene.ui_input.update_text_input(
                input_manager.text_input,
            )
            if input_manager.text_input:
                print(
                    "UI TEXT INPUT:",
                    repr(input_manager.text_input),
                )

            # --------------------------------------------------
            # Update UI
            # --------------------------------------------------

            scene.ui.update_input(
                scene.ui_input,
            )

            # --------------------------------------------------
            # SDL text input
            # --------------------------------------------------

            if scene.ui.focused_node is not None:
                input_manager.start_text_input()
            else:
                input_manager.stop_text_input()

            # --------------------------------------------------
            # Render
            # --------------------------------------------------

            if not renderer.begin_frame():
                input_manager.end_frame()
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

            input_manager.end_frame()

            time.sleep(0.001)

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