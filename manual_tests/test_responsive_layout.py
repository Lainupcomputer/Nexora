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
    print(" Nexora Responsive Layout Test")
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
            title="Nexora - Responsive Layout Test",
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
            "ResponsiveLayoutTest"
        )

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # ======================================================
        # Root layout
        # ======================================================

        root_layout = scene.ui.create_child(
            "RootLayout",
            node_type=HBoxContainer,
        )

        root_layout.width_mode = "fill"
        root_layout.height_mode = "fill"

        root_layout.spacing = 12.0

        root_layout.padding_left = 20.0
        root_layout.padding_top = 20.0
        root_layout.padding_right = 20.0
        root_layout.padding_bottom = 20.0

        root_layout.alignment = "stretch"

        # ======================================================
        # Sidebar
        # ======================================================

        sidebar = root_layout.create_child(
            "Sidebar",
            node_type=VBoxContainer,
        )

        sidebar.width_mode = "percent"
        sidebar.width_percent = 0.30

        sidebar.height_mode = "fill"

        sidebar.min_size = (
            220.0,
            0.0,
        )

        sidebar.spacing = 10.0

        sidebar.padding_left = 15.0
        sidebar.padding_top = 15.0
        sidebar.padding_right = 15.0
        sidebar.padding_bottom = 15.0

        sidebar.alignment = "stretch"

        # ------------------------------------------------------
        # Sidebar header
        # ------------------------------------------------------

        sidebar_header = sidebar.create_child(
            "SidebarHeader",
            node_type=Panel,
        )

        sidebar_header.height_mode = "fixed"

        sidebar_header.size = (
            0.0,
            70.0,
        )

        sidebar_header.min_size = (
            0.0,
            70.0,
        )

        sidebar_header.background = (
            55,
            70,
            110,
            255,
        )

        # ------------------------------------------------------
        # Sidebar grow area
        # ------------------------------------------------------

        sidebar_content = sidebar.create_child(
            "SidebarContent",
            node_type=Panel,
        )

        sidebar_content.layout_grow = 1.0

        sidebar_content.min_size = (
            0.0,
            100.0,
        )

        sidebar_content.background = (
            45,
            60,
            75,
            255,
        )

        # ------------------------------------------------------
        # Sidebar buttons
        # ------------------------------------------------------

        sidebar_buttons = sidebar.create_child(
            "SidebarButtons",
            node_type=VBoxContainer,
        )

        sidebar_buttons.height_mode = "content"

        sidebar_buttons.fit_content = True

        sidebar_buttons.spacing = 8.0

        sidebar_buttons.alignment = "stretch"

        button_a = sidebar_buttons.create_child(
            "ButtonA",
            node_type=Button,
        )

        button_a.text = "Dashboard"

        button_a.size = (
            0.0,
            50.0,
        )

        button_a.min_size = (
            0.0,
            50.0,
        )

        button_b = sidebar_buttons.create_child(
            "ButtonB",
            node_type=Button,
        )

        button_b.text = "Settings"

        button_b.size = (
            0.0,
            50.0,
        )

        button_b.min_size = (
            0.0,
            50.0,
        )

        button_c = sidebar_buttons.create_child(
            "ButtonC",
            node_type=Button,
        )

        button_c.text = "Exit"

        button_c.size = (
            0.0,
            50.0,
        )

        button_c.min_size = (
            0.0,
            50.0,
        )

        # ======================================================
        # Main content
        # ======================================================

        content = root_layout.create_child(
            "Content",
            node_type=VBoxContainer,
        )

        content.width_mode = "fill"
        content.height_mode = "fill"

        content.layout_grow = 1.0

        content.spacing = 12.0

        content.padding_left = 15.0
        content.padding_top = 15.0
        content.padding_right = 15.0
        content.padding_bottom = 15.0

        content.alignment = "stretch"

        # ------------------------------------------------------
        # Content header
        # ------------------------------------------------------

        content_header = content.create_child(
            "ContentHeader",
            node_type=Panel,
        )

        content_header.size = (
            0.0,
            80.0,
        )

        content_header.min_size = (
            0.0,
            80.0,
        )

        content_header.background = (
            70,
            90,
            130,
            255,
        )

        # ------------------------------------------------------
        # Content body
        # ------------------------------------------------------

        content_body = content.create_child(
            "ContentBody",
            node_type=Panel,
        )

        content_body.layout_grow = 1.0

        content_body.min_size = (
            0.0,
            150.0,
        )

        content_body.background = (
            45,
            100,
            70,
            255,
        )

        # ------------------------------------------------------
        # Content footer
        # ------------------------------------------------------

        content_footer = content.create_child(
            "ContentFooter",
            node_type=Panel,
        )

        content_footer.size = (
            0.0,
            60.0,
        )

        content_footer.min_size = (
            0.0,
            60.0,
        )

        content_footer.background = (
            120,
            75,
            60,
            255,
        )

        # ======================================================
        # Callbacks
        # ======================================================

        button_a.on_click = lambda: print(
            "[Sidebar] Dashboard"
        )

        button_b.on_click = lambda: print(
            "[Sidebar] Settings"
        )

        button_c.on_click = lambda: print(
            "[Sidebar] Exit"
        )

        # ======================================================
        # Instructions
        # ======================================================

        print("Test:")
        print()
        print("RootLayout:")
        print("  width_mode  = fill")
        print("  height_mode = fill")
        print()
        print("Sidebar:")
        print("  width = 30%")
        print("  minimum width = 220")
        print()
        print("Content:")
        print("  fills remaining width")
        print()
        print("Resize the window.")
        print()
        print("Expected:")
        print("  Root follows viewport.")
        print("  Sidebar changes with viewport width.")
        print("  Content uses the remaining space.")
        print("  Vertical grow areas resize automatically.")
        print()
        print("TAB / SHIFT+TAB should still navigate buttons.")
        print("ESC closes the test.")
        print()

        # ======================================================
        # Debug state
        # ======================================================

        last_debug_state = None
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
            # Responsive layout debug
            # --------------------------------------------------

            debug_state = (
                round(
                    scene.ui.size[0],
                    1,
                ),
                round(
                    scene.ui.size[1],
                    1,
                ),
                round(
                    root_layout.size[0],
                    1,
                ),
                round(
                    root_layout.size[1],
                    1,
                ),
                round(
                    sidebar.size[0],
                    1,
                ),
                round(
                    sidebar.size[1],
                    1,
                ),
                round(
                    content.size[0],
                    1,
                ),
                round(
                    content.size[1],
                    1,
                ),
                round(
                    sidebar_content.size[1],
                    1,
                ),
                round(
                    content_body.size[1],
                    1,
                ),
            )

            if debug_state != last_debug_state:
                print()
                print(
                    "[Layout]"
                )

                print(
                    f"  Viewport: "
                    f"{debug_state[0]} x "
                    f"{debug_state[1]}"
                )

                print(
                    f"  Root:     "
                    f"{debug_state[2]} x "
                    f"{debug_state[3]}"
                )

                print(
                    f"  Sidebar:  "
                    f"{debug_state[4]} x "
                    f"{debug_state[5]}"
                )

                print(
                    f"  Content:  "
                    f"{debug_state[6]} x "
                    f"{debug_state[7]}"
                )

                print(
                    f"  Sidebar grow height: "
                    f"{debug_state[8]}"
                )

                print(
                    f"  Content grow height: "
                    f"{debug_state[9]}"
                )

                last_debug_state = (
                    debug_state
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