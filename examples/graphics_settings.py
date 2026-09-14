from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.input import InputManager
from nexora.nodes import (
    Button,
    CheckBox,
    Dropdown,
    Label,
    Panel,
    Slider,
)
from nexora.rendering import Renderer
from nexora.rendering.gpu import (
    GPUContext,
    WindowMode,
)
from nexora.rendering.text import TextSystem
from nexora.scene import Scene
from nexora.settings import GraphicsSettings
from nexora.threading.context import ThreadContext


ROOT = Path(__file__).resolve().parent.parent

FONT_PATH = (
    ROOT
    / "assets"
    / "fonts"
    / "Roboto-Regular.ttf"
)


RESOLUTIONS = [
    "1280x720",
    "1600x900",
    "1920x1080",
]

WINDOW_MODES = [
    "windowed",
    "borderless",
    "fullscreen",
]

FRAMES_IN_FLIGHT = [
    "1",
    "2",
    "3",
]


def main() -> None:
    print("=" * 60)
    print(" Nexora Graphics Settings UI Example")
    print("=" * 60)
    print()

    if not FONT_PATH.is_file():
        raise FileNotFoundError(
            f"Font not found: {FONT_PATH}"
        )

    ThreadContext.initialize()

    text_system = TextSystem()
    text_system.initialize()

    graphics = GraphicsSettings(
        settings_path="settings",
    )

    gpu_settings = (
        graphics.gpu_context_kwargs()
    )

    context = None
    renderer = None
    input_manager = None
    scene = None
    font = None

    try:
        # ======================================================
        # GPU
        # ======================================================

        context = GPUContext(
            width=gpu_settings["width"],
            height=gpu_settings["height"],
            title="Nexora - Graphics Settings",
            vsync=gpu_settings["vsync"],
            resizable=gpu_settings["resizable"],
            frames_in_flight=(
                gpu_settings["frames_in_flight"]
            ),
            window_mode=WindowMode(
                gpu_settings["window_mode"]
            ),
        )

        # ======================================================
        # Font
        # ======================================================

        font = text_system.font(
            FONT_PATH,
            24,
        )

        # ======================================================
        # Renderer
        # ======================================================

        renderer = Renderer(
            context,
            font=font,
        )

        graphics.apply_post_processing(
            renderer
        )

        # ======================================================
        # Input
        # ======================================================

        input_manager = InputManager()

        input_manager.initialize(
            context.window
        )

        # ======================================================
        # Scene
        # ======================================================

        scene = Scene(
            "GraphicsSettingsUI"
        )

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # ======================================================
        # Main panel
        # ======================================================

        panel = scene.ui.create_child(
            "SettingsPanel",
            node_type=Panel,
        )

        panel.anchor = (
            0.5,
            0.5,
        )

        panel.pivot = (
            0.5,
            0.5,
        )

        panel.position = (
            -250.0,
            0.0,
        )

        panel.size = (
            500.0,
            650.0,
        )

        panel.background = (
            24,
            26,
            30,
            245,
        )

        panel.border_color = (
            70,
            72,
            80,
            255,
        )

        panel.border_width = 1.0
        panel.border_radius = 8.0

        # ======================================================
        # Title
        # ======================================================

        title = panel.create_child(
            "Title",
            node_type=Label,
        )

        title.text = (
            "Graphics Settings"
        )

        title.anchor = (
            0.5,
            0.0,
        )

        title.pivot = (
            0.5,
            0.0,
        )

        title.position = (
            0.0,
            30.0,
        )

        title.scale = 1.3

        # ======================================================
        # Resolution
        # ======================================================

        resolution_label = panel.create_child(
            "ResolutionLabel",
            node_type=Label,
        )

        resolution_label.text = (
            "Resolution"
        )

        resolution_label.position = (
            40.0,
            100.0,
        )

        resolution = panel.create_child(
            "Resolution",
            node_type=Dropdown,
        )

        resolution.position = (
            230.0,
            95.0,
        )

        resolution.size = (
            220.0,
            42.0,
        )

        resolution.set_options(
            RESOLUTIONS
        )

        current_resolution = (
            f"{graphics.window.width}x"
            f"{graphics.window.height}"
        )

        try:
            resolution_index = (
                RESOLUTIONS.index(
                    current_resolution
                )
            )

        except ValueError:
            resolution_index = 0

        resolution.set_selected_index(
            resolution_index,
            emit=False,
        )

        # ======================================================
        # Window mode
        # ======================================================

        mode_label = panel.create_child(
            "ModeLabel",
            node_type=Label,
        )

        mode_label.text = (
            "Window Mode"
        )

        mode_label.position = (
            40.0,
            160.0,
        )

        mode = panel.create_child(
            "Mode",
            node_type=Dropdown,
        )

        mode.position = (
            230.0,
            155.0,
        )

        mode.size = (
            220.0,
            42.0,
        )

        mode.set_options(
            WINDOW_MODES
        )

        try:
            mode_index = (
                WINDOW_MODES.index(
                    graphics.window.mode
                )
            )

        except ValueError:
            mode_index = 0

        mode.set_selected_index(
            mode_index,
            emit=False,
        )

        # ======================================================
        # Resizable
        # ======================================================

        resizable = panel.create_child(
            "Resizable",
            node_type=CheckBox,
        )

        resizable.text = (
            "Resizable Window"
        )

        resizable.position = (
            40.0,
            220.0,
        )

        resizable.set_checked(
            bool(
                graphics.window.resizable
            ),
            emit=False,
        )

        # ======================================================
        # VSync
        # ======================================================

        vsync = panel.create_child(
            "VSync",
            node_type=CheckBox,
        )

        vsync.text = "VSync"

        vsync.position = (
            40.0,
            270.0,
        )

        vsync.set_checked(
            bool(
                graphics.rendering.vsync
            ),
            emit=False,
        )

        # ======================================================
        # Frames in flight
        # ======================================================

        fif_label = panel.create_child(
            "FramesLabel",
            node_type=Label,
        )

        fif_label.text = (
            "Frames in Flight"
        )

        fif_label.position = (
            40.0,
            330.0,
        )

        fif = panel.create_child(
            "FramesInFlight",
            node_type=Dropdown,
        )

        fif.position = (
            230.0,
            325.0,
        )

        fif.size = (
            220.0,
            42.0,
        )

        fif.set_options(
            FRAMES_IN_FLIGHT
        )

        current_fif = str(
            graphics.rendering.frames_in_flight
        )

        fif.set_selected_index(
            FRAMES_IN_FLIGHT.index(
                current_fif
            ),
            emit=False,
        )

        # ======================================================
        # Post processing
        # ======================================================

        post_enabled = panel.create_child(
            "PostProcessing",
            node_type=CheckBox,
        )

        post_enabled.text = (
            "Post Processing"
        )

        post_enabled.position = (
            40.0,
            390.0,
        )

        post_enabled.set_checked(
            bool(
                graphics.post_processing.enabled
            ),
            emit=False,
        )

        # ======================================================
        # Brightness
        # ======================================================

        brightness_label = panel.create_child(
            "BrightnessLabel",
            node_type=Label,
        )

        brightness_label.text = (
            "Brightness"
        )

        brightness_label.position = (
            40.0,
            450.0,
        )

        brightness = panel.create_child(
            "Brightness",
            node_type=Slider,
        )

        brightness.position = (
            230.0,
            455.0,
        )

        brightness.length = 180.0
        brightness.min_value = 0.5
        brightness.max_value = 1.5
        brightness.step = 0.05

        brightness.set_value(
            float(
                graphics.post_processing.brightness
            ),
            emit=False,
        )

        # ======================================================
        # Contrast
        # ======================================================

        contrast_label = panel.create_child(
            "ContrastLabel",
            node_type=Label,
        )

        contrast_label.text = (
            "Contrast"
        )

        contrast_label.position = (
            40.0,
            500.0,
        )

        contrast = panel.create_child(
            "Contrast",
            node_type=Slider,
        )

        contrast.position = (
            230.0,
            505.0,
        )

        contrast.length = 180.0
        contrast.min_value = 0.5
        contrast.max_value = 1.5
        contrast.step = 0.05

        contrast.set_value(
            float(
                graphics.post_processing.contrast
            ),
            emit=False,
        )

        # ======================================================
        # Saturation
        # ======================================================

        saturation_label = panel.create_child(
            "SaturationLabel",
            node_type=Label,
        )

        saturation_label.text = (
            "Saturation"
        )

        saturation_label.position = (
            40.0,
            550.0,
        )

        saturation = panel.create_child(
            "Saturation",
            node_type=Slider,
        )

        saturation.position = (
            230.0,
            555.0,
        )

        saturation.length = 180.0
        saturation.min_value = 0.0
        saturation.max_value = 2.0
        saturation.step = 0.05

        saturation.set_value(
            float(
                graphics.post_processing.saturation
            ),
            emit=False,
        )

        # ======================================================
        # Film grain
        # ======================================================

        grain_label = panel.create_child(
            "GrainLabel",
            node_type=Label,
        )

        grain_label.text = (
            "Film Grain"
        )

        grain_label.position = (
            40.0,
            600.0,
        )

        grain = panel.create_child(
            "FilmGrain",
            node_type=Slider,
        )

        grain.position = (
            230.0,
            605.0,
        )

        grain.length = 180.0
        grain.min_value = 0.0
        grain.max_value = 1.0
        grain.step = 0.05

        grain.set_value(
            float(
                graphics.post_processing.film_grain
            ),
            emit=False,
        )

        # ======================================================
        # Preview
        # ======================================================

        preview = scene.ui.create_child(
            "Preview",
            node_type=Panel,
        )

        preview.anchor = (
            0.5,
            0.5,
        )

        preview.pivot = (
            0.5,
            0.5,
        )

        preview.position = (
            320.0,
            0.0,
        )

        preview.size = (
            420.0,
            650.0,
        )

        preview.background = (
            18,
            20,
            24,
            255,
        )

        preview.border_color = (
            70,
            72,
            80,
            255,
        )

        preview.border_width = 1.0
        preview.border_radius = 8.0

        preview_title = preview.create_child(
            "PreviewTitle",
            node_type=Label,
        )

        preview_title.text = (
            "Post Processing Preview"
        )

        preview_title.anchor = (
            0.5,
            0.0,
        )

        preview_title.pivot = (
            0.5,
            0.0,
        )

        preview_title.position = (
            0.0,
            30.0,
        )

        # ======================================================
        # Preview colors
        # ======================================================

        red_panel = preview.create_child(
            "Red",
            node_type=Panel,
        )

        red_panel.position = (
            45.0,
            110.0,
        )

        red_panel.size = (
            330.0,
            100.0,
        )

        red_panel.background = (
            210,
            55,
            55,
            255,
        )

        green_panel = preview.create_child(
            "Green",
            node_type=Panel,
        )

        green_panel.position = (
            45.0,
            235.0,
        )

        green_panel.size = (
            330.0,
            100.0,
        )

        green_panel.background = (
            55,
            190,
            95,
            255,
        )

        blue_panel = preview.create_child(
            "Blue",
            node_type=Panel,
        )

        blue_panel.position = (
            45.0,
            360.0,
        )

        blue_panel.size = (
            330.0,
            100.0,
        )

        blue_panel.background = (
            60,
            105,
            220,
            255,
        )

        # ======================================================
        # Status
        # ======================================================

        status = preview.create_child(
            "Status",
            node_type=Label,
        )

        status.anchor = (
            0.5,
            1.0,
        )

        status.pivot = (
            0.5,
            1.0,
        )

        status.position = (
            0.0,
            -80.0,
        )

        status.text = (
            "Change settings and press Apply"
        )

        # ======================================================
        # Buttons
        # ======================================================

        apply_button = preview.create_child(
            "Apply",
            node_type=Button,
        )

        apply_button.text = "Apply"

        apply_button.anchor = (
            0.0,
            1.0,
        )

        apply_button.pivot = (
            0.0,
            1.0,
        )

        apply_button.position = (
            40.0,
            -25.0,
        )

        apply_button.size = (
            150.0,
            45.0,
        )

        reset_button = preview.create_child(
            "Reset",
            node_type=Button,
        )

        reset_button.text = "Reset"

        reset_button.anchor = (
            1.0,
            1.0,
        )

        reset_button.pivot = (
            1.0,
            1.0,
        )

        reset_button.position = (
            -40.0,
            -25.0,
        )

        reset_button.size = (
            150.0,
            45.0,
        )

        # ======================================================
        # Apply
        # ======================================================

        def apply_settings() -> None:
            selected_resolution = (
                resolution.options[
                    resolution.selected_index
                ]
            )

            width_text, height_text = (
                selected_resolution.split(
                    "x"
                )
            )

            graphics.window.width = int(
                width_text
            )

            graphics.window.height = int(
                height_text
            )

            graphics.window.mode = (
                mode.options[
                    mode.selected_index
                ]
            )

            graphics.window.resizable = (
                resizable.checked
            )

            graphics.rendering.vsync = (
                vsync.checked
            )

            graphics.rendering.frames_in_flight = int(
                fif.options[
                    fif.selected_index
                ]
            )

            graphics.post_processing.enabled = (
                post_enabled.checked
            )

            graphics.post_processing.brightness = (
                brightness.value
            )

            graphics.post_processing.contrast = (
                contrast.value
            )

            graphics.post_processing.saturation = (
                saturation.value
            )

            graphics.post_processing.film_grain = (
                grain.value
            )

            graphics.apply_runtime(
                context,
                renderer,
            )

            scene.ui.set_viewport_size(
                renderer.width,
                renderer.height,
            )

            status.text = (
                "Settings applied and saved"
            )

            print()
            print(
                "Graphics settings applied"
            )

            print(
                graphics.data
            )

        apply_button.on_click = (
            apply_settings
        )

        # ======================================================
        # Reset
        # ======================================================

        def reset_settings() -> None:
            graphics.reset_user()

            current_resolution = (
                f"{graphics.window.width}x"
                f"{graphics.window.height}"
            )

            if (
                current_resolution
                in RESOLUTIONS
            ):
                resolution.set_selected_index(
                    RESOLUTIONS.index(
                        current_resolution
                    ),
                    emit=False,
                )

            if (
                graphics.window.mode
                in WINDOW_MODES
            ):
                mode.set_selected_index(
                    WINDOW_MODES.index(
                        graphics.window.mode
                    ),
                    emit=False,
                )

            resizable.set_checked(
                bool(
                    graphics.window.resizable
                ),
                emit=False,
            )

            vsync.set_checked(
                bool(
                    graphics.rendering.vsync
                ),
                emit=False,
            )

            current_fif = str(
                graphics.rendering.frames_in_flight
            )

            if (
                current_fif
                in FRAMES_IN_FLIGHT
            ):
                fif.set_selected_index(
                    FRAMES_IN_FLIGHT.index(
                        current_fif
                    ),
                    emit=False,
                )

            post_enabled.set_checked(
                bool(
                    graphics.post_processing.enabled
                ),
                emit=False,
            )

            brightness.set_value(
                float(
                    graphics.post_processing.brightness
                ),
                emit=False,
            )

            contrast.set_value(
                float(
                    graphics.post_processing.contrast
                ),
                emit=False,
            )

            saturation.set_value(
                float(
                    graphics.post_processing.saturation
                ),
                emit=False,
            )

            grain.set_value(
                float(
                    graphics.post_processing.film_grain
                ),
                emit=False,
            )

            graphics.apply_runtime(
                context,
                renderer,
            )

            scene.ui.set_viewport_size(
                renderer.width,
                renderer.height,
            )

            status.text = (
                "User settings reset"
            )

        reset_button.on_click = (
            reset_settings
        )

        # ======================================================
        # Live post-processing preview
        # ======================================================

        def update_post_processing(
            _value=None,
        ) -> None:
            renderer.post_processing.enabled = (
                post_enabled.checked
            )

            renderer.post_processing.brightness = (
                brightness.value
            )

            renderer.post_processing.contrast = (
                contrast.value
            )

            renderer.post_processing.saturation = (
                saturation.value
            )

            renderer.post_processing.film_grain = (
                grain.value
            )

        post_enabled.on_change = (
            update_post_processing
        )

        brightness.on_change = (
            update_post_processing
        )

        contrast.on_change = (
            update_post_processing
        )

        saturation.on_change = (
            update_post_processing
        )

        grain.on_change = (
            update_post_processing
        )

        # ======================================================
        # Loop
        # ======================================================

        running = True

        while running:
            events = list(
                context.poll_events()
            )

            for event in events:
                if (
                    event.type
                    == sdl3.SDL_EVENT_QUIT
                ):
                    running = False

            input_manager.begin_frame(
                events
            )

            if (
                input_manager.key_pressed(
                    "escape"
                )
            ):
                running = False

            # ==================================================
            # UI input
            # ==================================================

            mouse_x, mouse_y = (
                input_manager.mouse_position
            )

            wheel_x, wheel_y = (
                input_manager.wheel
            )

            ui_mouse_x = (
                mouse_x
                - renderer.width / 2.0
            )

            ui_mouse_y = (
                mouse_y
                - renderer.height / 2.0
            )

            scene.ui_input.update_mouse(
                position=(
                    ui_mouse_x,
                    ui_mouse_y,
                ),
                down=input_manager.mouse_down(
                    "left"
                ),
                pressed=input_manager.mouse_pressed(
                    "left"
                ),
                released=input_manager.mouse_released(
                    "left"
                ),
                wheel_x=wheel_x,
                wheel_y=wheel_y,
            )

            scene.ui_input.update_keyboard(
                keys_down=(
                    input_manager.keys_down
                ),
                keys_pressed=(
                    input_manager.keys_pressed
                ),
                keys_released=(
                    input_manager.keys_released
                ),
            )

            scene.ui_input.update_text_input(
                input_manager.text_input
            )

            scene.ui.update_input(
                scene.ui_input
            )

            # ==================================================
            # Render
            # ==================================================

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
                    running = False

            except Exception:
                context.cancel_frame()
                raise

            input_manager.end_frame()

            time.sleep(
                0.001
            )

    finally:
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


if __name__ == "__main__":
    main()