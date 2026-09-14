from __future__ import annotations

import time
from ctypes import c_float
from pathlib import Path

import sdl3

from nexora.audio import (
    AudioChannel,
    AudioSource,
    AudioSystem,
)

from nexora.nodes import (
    Button,
    Label,
    Slider,
)

from nexora.rendering.gpu.context import (
    GPUContext,
)

from nexora.rendering.renderer import (
    Renderer,
)

from nexora.rendering.text import (
    TextSystem,
)

from nexora.scene import Scene
from nexora.ui import UIInput


# ==============================================================
# PATHS
# ==============================================================

ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

FONT_PATH = (
    ROOT
    / "assets"
    / "fonts"
    / "Roboto-Regular.ttf"
)

KICK_PATH = (
    ROOT
    / "assets"
    / "audio"
    / "kick.wav"
)

HAT_PATH = (
    ROOT
    / "assets"
    / "audio"
    / "hihat.wav"
)

SNARE_PATH = (
    ROOT
    / "assets"
    / "audio"
    / "snare.wav"
)


# ==============================================================
# CONFIG
# ==============================================================

STEP_COUNT = 16

WINDOW_WIDTH = 1500
WINDOW_HEIGHT = 850


# ==============================================================
# TRACK
# ==============================================================


class SequencerTrack:
    def __init__(
        self,
        name: str,
        source: AudioSource,
    ) -> None:
        self.name = name
        self.source = source

        self.steps = [
            False
            for _ in range(
                STEP_COUNT
            )
        ]

        self.volume = 1.0
        self.pitch = 1.0

        self.buttons: list[
            Button
        ] = []


# ==============================================================
# MAIN
# ==============================================================


def main() -> None:
    print()
    print("=" * 70)
    print(" Nexora Step Sequencer UI Example")
    print("=" * 70)
    print()

    # ----------------------------------------------------------
    # Check assets
    # ----------------------------------------------------------

    required_files = (
        FONT_PATH,
        KICK_PATH,
        HAT_PATH,
        SNARE_PATH,
    )

    for path in required_files:
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing asset: {path}"
            )

    # ==========================================================
    # TEXT
    # ==============================================================

    text_system = TextSystem()
    text_system.initialize()

    context = None
    renderer = None
    font = None
    audio = None
    scene = None

    try:
        # ======================================================
        # GPU
        # ======================================================

        context = GPUContext(
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            title="Nexora - Step Sequencer",
            debug=True,
            vsync=True,
            resizable=True,
        )

        # ======================================================
        # FONT
        # ======================================================

        font = text_system.font(
            FONT_PATH,
            24,
        )

        # ======================================================
        # RENDERER
        # ======================================================

        renderer = Renderer(
            context,
            font=font,
        )

        # ======================================================
        # AUDIO
        # ======================================================

        audio = AudioSystem()
        audio.initialize()

        kick_sound = audio.load(
            str(
                KICK_PATH
            )
        )

        hat_sound = audio.load(
            str(
                HAT_PATH
            )
        )

        snare_sound = audio.load(
            str(
                SNARE_PATH
            )
        )

        sfx_bus = audio.get_bus(
            "SFX"
        )

        kick_source = AudioSource(
            kick_sound,
            channel=AudioChannel.SFX,
            volume=1.0,
            pitch=1.0,
            bus=sfx_bus,
        )

        hat_source = AudioSource(
            hat_sound,
            channel=AudioChannel.SFX,
            volume=0.8,
            pitch=1.0,
            bus=sfx_bus,
        )

        snare_source = AudioSource(
            snare_sound,
            channel=AudioChannel.SFX,
            volume=1.0,
            pitch=1.0,
            bus=sfx_bus,
        )

        audio.player.add(
            kick_source
        )

        audio.player.add(
            hat_source
        )

        audio.player.add(
            snare_source
        )

        tracks = [
            SequencerTrack(
                "Kick",
                kick_source,
            ),
            SequencerTrack(
                "Hi-Hat",
                hat_source,
            ),
            SequencerTrack(
                "Snare",
                snare_source,
            ),
        ]

        # ======================================================
        # DEFAULT PATTERN
        # ======================================================

        # Kick
        for step in (
            0,
            4,
            8,
            12,
        ):
            tracks[0].steps[
                step
            ] = True

        # Hi-hat
        for step in range(
            0,
            STEP_COUNT,
            2,
        ):
            tracks[1].steps[
                step
            ] = True

        # Snare
        for step in (
            4,
            12,
        ):
            tracks[2].steps[
                step
            ] = True

        # ======================================================
        # SCENE
        # ======================================================

        scene = Scene(
            "StepSequencer"
        )

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # ======================================================
        # TITLE
        # ======================================================

        title = scene.ui.create_child(
            "Title",
            node_type=Label,
        )

        title.text = (
            "NEXORA STEP SEQUENCER"
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

        title.scale = 1.4

        # ======================================================
        # TRANSPORT
        # ======================================================

        play_button = (
            scene.ui.create_child(
                "PlayButton",
                node_type=Button,
            )
        )

        play_button.size = (
            130.0,
            46.0,
        )

        play_button.anchor = (
            0.5,
            0.0,
        )

        play_button.pivot = (
            0.5,
            0.0,
        )

        play_button.position = (
            -80.0,
            90.0,
        )

        play_button.text = "PLAY"

        stop_button = (
            scene.ui.create_child(
                "StopButton",
                node_type=Button,
            )
        )

        stop_button.size = (
            130.0,
            46.0,
        )

        stop_button.anchor = (
            0.5,
            0.0,
        )

        stop_button.pivot = (
            0.5,
            0.0,
        )

        stop_button.position = (
            80.0,
            90.0,
        )

        stop_button.text = "STOP"

        # ======================================================
        # STATUS
        # ======================================================

        status_label = (
            scene.ui.create_child(
                "Status",
                node_type=Label,
            )
        )

        status_label.text = (
            "STOPPED"
        )

        status_label.anchor = (
            0.5,
            0.0,
        )

        status_label.pivot = (
            0.5,
            0.0,
        )

        status_label.position = (
            0.0,
            150.0,
        )

        # ======================================================
        # BPM
        # ======================================================

        bpm = 174.0

        bpm_label = (
            scene.ui.create_child(
                "BPMLabel",
                node_type=Label,
            )
        )

        bpm_label.text = (
            f"BPM: {bpm:.0f}"
        )

        bpm_label.anchor = (
            0.0,
            0.0,
        )

        bpm_label.pivot = (
            0.0,
            0.0,
        )

        bpm_label.position = (
            70.0,
            100.0,
        )

        bpm_slider = (
            scene.ui.create_child(
                "BPMSlider",
                node_type=Slider,
            )
        )

        bpm_slider.anchor = (
            0.0,
            0.0,
        )

        bpm_slider.pivot = (
            0.0,
            0.0,
        )

        bpm_slider.position = (
            70.0,
            145.0,
        )

        bpm_slider.length = 260.0

        bpm_slider.min_value = 60.0
        bpm_slider.max_value = 220.0
        bpm_slider.step = 1.0

        bpm_slider.set_value(
            bpm,
            emit=False,
        )

        # ======================================================
        # MASTER
        # ======================================================

        master_volume = 0.8

        master_label = (
            scene.ui.create_child(
                "MasterLabel",
                node_type=Label,
            )
        )

        master_label.text = (
            "MASTER: 80%"
        )

        master_label.anchor = (
            1.0,
            0.0,
        )

        master_label.pivot = (
            1.0,
            0.0,
        )

        master_label.position = (
            -70.0,
            100.0,
        )

        master_slider = (
            scene.ui.create_child(
                "MasterSlider",
                node_type=Slider,
            )
        )

        master_slider.anchor = (
            1.0,
            0.0,
        )

        master_slider.pivot = (
            1.0,
            0.0,
        )

        master_slider.position = (
            -70.0,
            145.0,
        )

        master_slider.length = (
            260.0
        )

        master_slider.min_value = 0.0
        master_slider.max_value = 1.0
        master_slider.step = 0.01

        master_slider.set_value(
            master_volume,
            emit=False,
        )

        audio.set_volume(
            AudioChannel.MASTER,
            master_volume,
        )

        # ======================================================
        # STEP NUMBERS
        # ======================================================

        grid_start_x = -500.0
        grid_start_y = -70.0

        step_spacing = 62.0

        for step in range(
            STEP_COUNT
        ):
            label = (
                scene.ui.create_child(
                    f"StepLabel{step}",
                    node_type=Label,
                )
            )

            label.text = (
                str(
                    step + 1
                )
            )

            label.anchor = (
                0.5,
                0.5,
            )

            label.pivot = (
                0.5,
                0.5,
            )

            label.position = (
                grid_start_x
                + step
                * step_spacing,
                grid_start_y
                - 55.0,
            )

            label.scale = 0.7

        # ======================================================
        # TRACK UI
        # ======================================================

        track_y_positions = [
            -70.0,
            20.0,
            110.0,
        ]

        for track_index, track in enumerate(
            tracks
        ):
            track_y = (
                track_y_positions[
                    track_index
                ]
            )

            # --------------------------------------------------
            # Track name
            # --------------------------------------------------

            track_label = (
                scene.ui.create_child(
                    f"{track.name}Label",
                    node_type=Label,
                )
            )

            track_label.text = (
                track.name
            )

            track_label.anchor = (
                0.5,
                0.5,
            )

            track_label.pivot = (
                1.0,
                0.5,
            )

            track_label.position = (
                grid_start_x
                - 35.0,
                track_y,
            )

            # --------------------------------------------------
            # Steps
            # --------------------------------------------------

            for step in range(
                STEP_COUNT
            ):
                button = (
                    scene.ui.create_child(
                        (
                            f"{track.name}"
                            f"Step{step}"
                        ),
                        node_type=Button,
                    )
                )

                button.size = (
                    48.0,
                    48.0,
                )

                button.anchor = (
                    0.5,
                    0.5,
                )

                button.pivot = (
                    0.5,
                    0.5,
                )

                button.position = (
                    grid_start_x
                    + step
                    * step_spacing,
                    track_y,
                )

                button.text = (
                    "X"
                    if track.steps[
                        step
                    ]
                    else ""
                )

                # ----------------------------------------------
                # Closure
                # ----------------------------------------------

                def make_step_callback(
                    target_track: SequencerTrack,
                    target_step: int,
                    target_button: Button,
                ):
                    def toggle() -> None:
                        target_track.steps[
                            target_step
                        ] = not (
                            target_track.steps[
                                target_step
                            ]
                        )

                        target_button.text = (
                            "X"
                            if target_track.steps[
                                target_step
                            ]
                            else ""
                        )

                    return toggle

                button.on_click = (
                    make_step_callback(
                        track,
                        step,
                        button,
                    )
                )

                track.buttons.append(
                    button
                )

            # ==================================================
            # VOLUME
            # ==================================================

            volume_label = (
                scene.ui.create_child(
                    f"{track.name}VolumeLabel",
                    node_type=Label,
                )
            )

            volume_label.text = (
                "VOL 100%"
            )

            volume_label.anchor = (
                0.5,
                0.5,
            )

            volume_label.position = (
                560.0,
                track_y - 15.0,
            )

            volume_label.scale = (
                0.7
            )

            volume_slider = (
                scene.ui.create_child(
                    f"{track.name}Volume",
                    node_type=Slider,
                )
            )

            volume_slider.anchor = (
                0.5,
                0.5,
            )

            volume_slider.position = (
                650.0,
                track_y + 15.0,
            )

            volume_slider.length = (
                140.0
            )

            volume_slider.min_value = (
                0.0
            )

            volume_slider.max_value = (
                1.0
            )

            volume_slider.step = (
                0.01
            )

            volume_slider.set_value(
                track.source.volume,
                emit=False,
            )

            def make_volume_callback(
                target_track: SequencerTrack,
                target_label: Label,
            ):
                def changed(
                    value: float,
                ) -> None:
                    target_track.volume = (
                        value
                    )

                    target_track.source.volume = (
                        value
                    )

                    target_label.text = (
                        f"VOL "
                        f"{value * 100:.0f}%"
                    )

                return changed

            volume_slider.on_change = (
                make_volume_callback(
                    track,
                    volume_label,
                )
            )

            # ==================================================
            # PITCH
            # ==================================================

            pitch_label = (
                scene.ui.create_child(
                    f"{track.name}PitchLabel",
                    node_type=Label,
                )
            )

            pitch_label.text = (
                "PITCH 1.00"
            )

            pitch_label.anchor = (
                0.5,
                0.5,
            )

            pitch_label.position = (
                560.0,
                track_y + 30.0,
            )

            pitch_label.scale = (
                0.7
            )

            pitch_slider = (
                scene.ui.create_child(
                    f"{track.name}Pitch",
                    node_type=Slider,
                )
            )

            pitch_slider.anchor = (
                0.5,
                0.5,
            )

            pitch_slider.position = (
                650.0,
                track_y + 55.0,
            )

            pitch_slider.length = (
                140.0
            )

            pitch_slider.min_value = (
                0.5
            )

            pitch_slider.max_value = (
                2.0
            )

            pitch_slider.step = (
                0.01
            )

            pitch_slider.set_value(
                1.0,
                emit=False,
            )

            def make_pitch_callback(
                target_track: SequencerTrack,
                target_label: Label,
            ):
                def changed(
                    value: float,
                ) -> None:
                    target_track.pitch = (
                        value
                    )

                    target_track.source.pitch = (
                        value
                    )

                    target_label.text = (
                        f"PITCH "
                        f"{value:.2f}"
                    )

                return changed

            pitch_slider.on_change = (
                make_pitch_callback(
                    track,
                    pitch_label,
                )
            )

        # ======================================================
        # CALLBACKS
        # ======================================================

        def bpm_changed(
            value: float,
        ) -> None:
            nonlocal bpm

            bpm = value

            bpm_label.text = (
                f"BPM: {bpm:.0f}"
            )

        bpm_slider.on_change = (
            bpm_changed
        )

        def master_changed(
            value: float,
        ) -> None:
            nonlocal master_volume

            master_volume = value

            audio.set_volume(
                AudioChannel.MASTER,
                value,
            )

            master_label.text = (
                f"MASTER: "
                f"{value * 100:.0f}%"
            )

        master_slider.on_change = (
            master_changed
        )

        # ======================================================
        # TRANSPORT STATE
        # ======================================================

        playing = False

        current_step = 0

        next_step_time = (
            time.perf_counter()
        )

        def play() -> None:
            nonlocal playing
            nonlocal current_step
            nonlocal next_step_time

            playing = True

            current_step = 0

            next_step_time = (
                time.perf_counter()
            )

            status_label.text = (
                "PLAYING"
            )

        def stop() -> None:
            nonlocal playing
            nonlocal current_step

            playing = False

            current_step = 0

            status_label.text = (
                "STOPPED"
            )

            for track in tracks:
                track.source.stop()

        play_button.on_click = (
            play
        )

        stop_button.on_click = (
            stop
        )

        # ======================================================
        # UI INPUT
        # ======================================================

        ui_input = UIInput()

        previous_mouse_down = False

        # ======================================================
        # MAIN LOOP
        # ======================================================

        print()
        print(
            "Step sequencer running."
        )
        print(
            "Click steps, adjust sliders, "
            "then press PLAY."
        )
        print()

        running = True

        while running:
            frame_start = (
                time.perf_counter()
            )

            # ==================================================
            # EVENTS
            # ==================================================

            for event in (
                context.poll_events()
            ):
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

            # ==================================================
            # MOUSE
            # ==================================================

            mouse_x = c_float(
                0.0
            )

            mouse_y = c_float(
                0.0
            )

            mouse_buttons = (
                sdl3.SDL_GetMouseState(
                    mouse_x,
                    mouse_y,
                )
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

            previous_mouse_down = (
                current_mouse_down
            )

            ui_mouse_x = (
                float(
                    mouse_x.value
                )
                - renderer.width
                / 2.0
            )

            ui_mouse_y = (
                float(
                    mouse_y.value
                )
                - renderer.height
                / 2.0
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

            scene.ui.update_input(
                ui_input
            )

            # ==================================================
            # SEQUENCER
            # ==================================================

            if playing:
                now = (
                    time.perf_counter()
                )

                # ----------------------------------------------
                # 16th-note duration
                #
                # beat = 60 / BPM
                # 16th = beat / 4
                # ----------------------------------------------

                step_duration = (
                    60.0
                    / bpm
                    / 4.0
                )

                while (
                    now
                    >= next_step_time
                ):
                    # ------------------------------------------
                    # Trigger tracks
                    # ------------------------------------------

                    for track in tracks:
                        if track.steps[
                            current_step
                        ]:
                            audio.player.play(
                                track.source
                            )

                    # ------------------------------------------
                    # Next step
                    # ------------------------------------------

                    current_step = (
                        current_step + 1
                    ) % STEP_COUNT

                    next_step_time += (
                        step_duration
                    )

            # ==================================================
            # AUDIO
            # ==================================================

            audio.player.update()

            # ==================================================
            # STEP VISUALS
            # ==================================================

            active_step = (
                current_step - 1
            ) % STEP_COUNT

            for track in tracks:
                for (
                    step_index,
                    button,
                ) in enumerate(
                    track.buttons
                ):
                    active = (
                        playing
                        and step_index
                        == active_step
                    )

                    enabled = (
                        track.steps[
                            step_index
                        ]
                    )

                    if active:
                        button.normal_background = (
                            70,
                            120,
                            70,
                            255,
                        )

                    elif enabled:
                        button.normal_background = (
                            55,
                            80,
                            110,
                            255,
                        )

                    else:
                        button.normal_background = (
                            32,
                            34,
                            37,
                            255,
                        )

            # ==================================================
            # RENDER
            # ==================================================

            if not renderer.begin_frame():
                time.sleep(
                    0.001
                )

                continue

            try:
                scene.ui.render(
                    renderer
                )

                renderer.end_frame()

            except Exception:
                context.cancel_frame()

                raise

            # ==================================================
            # SMALL CPU YIELD
            # ==================================================

            elapsed = (
                time.perf_counter()
                - frame_start
            )

            target = (
                1.0 / 144.0
            )

            remaining = (
                target
                - elapsed
            )

            if remaining > 0.0:
                time.sleep(
                    remaining
                )

    # ==========================================================
    # CLEANUP
    # ==============================================================

    finally:
        print()
        print(
            "Cleaning up..."
        )

        if audio is not None:
            audio.shutdown()

        if scene is not None:
            scene.destroy()

        if renderer is not None:
            renderer.destroy()

        if font is not None:
            font.close()

        if context is not None:
            context.destroy()

        text_system.shutdown()

        print(
            "Done."
        )


if __name__ == "__main__":
    main()