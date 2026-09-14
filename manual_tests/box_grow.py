from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.input.input import InputManager
from nexora.nodes import (
    Button,
    HBoxContainer,
    Panel,
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
    print("=" * 60)
    print(" Nexora Box Grow Layout Test")
    print("=" * 60)
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
            title="Nexora - Box Grow Test",
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
            28,
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
            "BoxGrowTest"
        )

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # ======================================================
        # LEFT: VBox grow test
        # ======================================================

        vbox = scene.ui.create_child(
            "VBoxGrow",
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
            -300.0,
            0.0,
        )

        vbox.size = (
            420.0,
            620.0,
        )

        vbox.spacing = 10.0

        vbox.padding_left = 15.0
        vbox.padding_top = 15.0
        vbox.padding_right = 15.0
        vbox.padding_bottom = 15.0

        vbox.alignment = "stretch"

        # ------------------------------------------------------
        # Header
        # ------------------------------------------------------

        header = vbox.create_child(
            "Header",
            node_type=Panel,
        )

        header.min_size = (
            0.0,
            70.0,
        )

        header.size = (
            100.0,
            70.0,
        )

        header.background = (
            65,
            80,
            120,
            255,
        )

        # ------------------------------------------------------
        # Content grow 1
        # ------------------------------------------------------

        content = vbox.create_child(
            "Content",
            node_type=Panel,
        )

        content.min_size = (
            0.0,
            100.0,
        )

        content.layout_grow = 1.0

        content.background = (
            55,
            110,
            70,
            255,
        )

        # ------------------------------------------------------
        # Footer
        # ------------------------------------------------------

        footer = vbox.create_child(
            "Footer",
            node_type=Panel,
        )

        footer.min_size = (
            0.0,
            60.0,
        )

        footer.size = (
            100.0,
            60.0,
        )

        footer.background = (
            120,
            75,
            60,
            255,
        )

        # ======================================================
        # RIGHT: HBox 1:2:1 grow test
        # ======================================================

        hbox = scene.ui.create_child(
            "HBoxGrow",
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
            300.0,
        )

        hbox.spacing = 10.0

        hbox.padding_left = 15.0
        hbox.padding_top = 15.0
        hbox.padding_right = 15.0
        hbox.padding_bottom = 15.0

        hbox.alignment = "stretch"

        # ------------------------------------------------------
        # Left = grow 1
        # ------------------------------------------------------

        left_panel = hbox.create_child(
            "Left",
            node_type=Panel,
        )

        left_panel.min_size = (
            80.0,
            0.0,
        )

        left_panel.layout_grow = 1.0

        left_panel.background = (
            90,
            70,
            130,
            255,
        )

        # ------------------------------------------------------
        # Center = grow 2
        # ------------------------------------------------------

        center_panel = hbox.create_child(
            "Center",
            node_type=Panel,
        )

        center_panel.min_size = (
            80.0,
            0.0,
        )

        center_panel.layout_grow = 2.0

        center_panel.background = (
            70,
            120,
            145,
            255,
        )

        # ------------------------------------------------------
        # Right = grow 1
        # ------------------------------------------------------

        right_panel = hbox.create_child(
            "Right",
            node_type=Panel,
        )

        right_panel.min_size = (
            80.0,
            0.0,
        )

        right_panel.layout_grow = 1.0

        right_panel.background = (
            135,
            85,
            80,
            255,
        )

        # ======================================================
        # Resize control buttons
        # ======================================================

        controls = scene.ui.create_child(
            "Controls",
            node_type=HBoxContainer,
        )

        controls.anchor = (
            0.5,
            1.0,
        )

        controls.pivot = (
            0.5,
            1.0,
        )

        controls.position = (
            0.0,
            -30.0,
        )

        controls.size = (
            700.0,
            70.0,
        )

        controls.spacing = 10.0
        controls.alignment = "center"

        shrink_button = controls.create_child(
            "Shrink",
            node_type=Button,
        )

        shrink_button.text = "Shrink VBox"

        shrink_button.size = (
            180.0,
            50.0,
        )

        grow_button = controls.create_child(
            "Grow",
            node_type=Button,
        )

        grow_button.text = "Grow VBox"

        grow_button.size = (
            180.0,
            50.0,
        )

        reset_button = controls.create_child(
            "Reset",
            node_type=Button,
        )

        reset_button.text = "Reset"

        reset_button.size = (
            180.0,
            50.0,
        )

        # ======================================================
        # Callbacks
        # ======================================================

        def shrink_vbox() -> None:
            width, height = vbox.size

            vbox.size = (
                width,
                max(
                    300.0,
                    height - 80.0,
                ),
            )

            print(
                f"[VBox] size = {vbox.size}"
            )

        def grow_vbox() -> None:
            width, height = vbox.size

            vbox.size = (
                width,
                min(
                    720.0,
                    height + 80.0,
                ),
            )

            print(
                f"[VBox] size = {vbox.size}"
            )

        def reset_layout() -> None:
            vbox.size = (
                420.0,
                620.0,
            )

            hbox.size = (
                520.0,
                300.0,
            )

            print(
                "[Layout] reset"
            )

        shrink_button.on_click = (
            shrink_vbox
        )

        grow_button.on_click = (
            grow_vbox
        )

        reset_button.on_click = (
            reset_layout
        )

        # ======================================================
        # Instructions
        # ======================================================

        print("Test:")
        print()
        print("LEFT - VBox:")
        print("  Header  = fixed 70 px")
        print("  Content = grow 1")
        print("  Footer  = fixed 60 px")
        print()
        print("RIGHT - HBox:")
        print("  Left   grow = 1")
        print("  Center grow = 2")
        print("  Right  grow = 1")
        print()
        print("Expected:")
        print("  Center should receive about twice")
        print("  as much free width as Left/Right.")
        print()
        print("Resize the window.")
        print("Use buttons at bottom to resize VBox.")
        print()
        print("ESC closes the test.")
        print()

        # ======================================================
        # Debug state
        # ======================================================

        last_sizes = None
        last_focus = None

        # ======================================================
        # Loop
        # ======================================================

        running = True

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
            # UI
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
            # Layout debug
            # --------------------------------------------------

            current_sizes = (
                round(
                    header.size[1],
                    2,
                ),
                round(
                    content.size[1],
                    2,
                ),
                round(
                    footer.size[1],
                    2,
                ),
                round(
                    left_panel.size[0],
                    2,
                ),
                round(
                    center_panel.size[0],
                    2,
                ),
                round(
                    right_panel.size[0],
                    2,
                ),
            )

            if current_sizes != last_sizes:
                print()

                print(
                    "[VBox]"
                )

                print(
                    "  Header :",
                    current_sizes[0],
                )

                print(
                    "  Content:",
                    current_sizes[1],
                )

                print(
                    "  Footer :",
                    current_sizes[2],
                )

                print()

                print(
                    "[HBox]"
                )

                print(
                    "  Left  :",
                    current_sizes[3],
                )

                print(
                    "  Center:",
                    current_sizes[4],
                )

                print(
                    "  Right :",
                    current_sizes[5],
                )

                print()

                last_sizes = (
                    current_sizes
                )

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