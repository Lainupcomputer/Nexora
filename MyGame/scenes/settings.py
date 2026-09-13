from __future__ import annotations

from collections.abc import Callable

from nexora.nodes import (
    Button,
    CheckBox,
    HBoxContainer,
    Label,
    ScrollView,
    Slider,
    VBoxContainer,
)
from nexora.scene import Scene
from nexora.settings import SettingsStore


class SettingsScene(Scene):
    def __init__(
        self,
        *,
        settings: SettingsStore,
        on_apply: Callable[[], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            "Settings"
        )

        # ==========================================================
        # Settings
        # ==========================================================

        self.settings = settings

        # ==========================================================
        # Callbacks
        # ==========================================================

        self._on_apply_callback = (
            on_apply
        )

        self._on_back_callback = (
            on_back
        )

        # ==========================================================
        # State
        # ==========================================================

        self._built = False

        # ==========================================================
        # Controls
        # ==========================================================

        self._fullscreen_checkbox: CheckBox | None = None
        self._vsync_checkbox: CheckBox | None = None

        self._master_slider: Slider | None = None
        self._music_slider: Slider | None = None
        self._sfx_slider: Slider | None = None

        self._master_value_label: Label | None = None
        self._music_value_label: Label | None = None
        self._sfx_value_label: Label | None = None

    # ==============================================================
    # Build
    # ==============================================================

    def build(
        self,
    ) -> None:
        if self._built:
            return

        self._built = True

        # ==========================================================
        # Root layout
        # ==========================================================

        root = self.ui.create_child(
            "SettingsRoot",
            node_type=VBoxContainer,
        )

        root.anchor = (
            0.5,
            0.5,
        )

        root.pivot = (
            0.5,
            0.5,
        )

        root.position = (
            0.0,
            0.0,
        )

        root.size = (
            820.0,
            700.0,
        )

        root.spacing = (
            10.0
        )

        root.alignment = (
            "center"
        )

        root.padding_left = (
            20.0
        )

        root.padding_right = (
            20.0
        )

        root.padding_top = (
            10.0
        )

        root.padding_bottom = (
            10.0
        )

        # ==========================================================
        # Fixed title
        # ==========================================================

        title = root.create_child(
            "Title",
            node_type=Label,
        )

        title.text = (
            "EINSTELLUNGEN"
        )

        title.scale = (
            1.7
        )

        title.size = (
            700.0,
            65.0,
        )

        title.pivot = (
            0.5,
            0.5,
        )

        # ==========================================================
        # ScrollView
        # ==========================================================

        scroll = root.create_child(
            "SettingsScroll",
            node_type=ScrollView,
        )

        scroll.size = (
            780.0,
            500.0,
        )

        scroll.scroll_speed = (
            18.0
        )

        scroll.background = (
            0,
            0,
            0,
            0,
        )

        scroll.border_radius = (
            0.0
        )

        # ==========================================================
        # Scroll content area
        # ==========================================================

        scroll.set_content_size(
            720.0,
            850.0,
        )

        content = scroll.create_content_child(
            "SettingsContent",
            node_type=VBoxContainer,
        )

        content.anchor = (
            0.5,
            0.5,
        )

        content.pivot = (
            0.5,
            0.5,
        )

        content.position = (
            0.0,
            0.0,
        )

        content.size = (
            720.0,
            850.0,
        )

        content.spacing = (
            14.0
        )

        content.alignment = (
            "center"
        )

        content.padding_left = (
            35.0
        )

        content.padding_right = (
            35.0
        )

        content.padding_top = (
            15.0
        )

        content.padding_bottom = (
            15.0
        )

        # ==========================================================
        # VIDEO
        # ==========================================================

        video_title = content.create_child(
            "VideoTitle",
            node_type=Label,
        )

        video_title.text = (
            "ANZEIGE"
        )

        video_title.scale = (
            1.15
        )

        video_title.size = (
            600.0,
            40.0,
        )

        video_title.pivot = (
            0.5,
            0.5,
        )

        # ----------------------------------------------------------
        # Fullscreen row
        # ----------------------------------------------------------

        fullscreen_row = content.create_child(
            "FullscreenRow",
            node_type=HBoxContainer,
        )

        fullscreen_row.size = (
            600.0,
            50.0,
        )

        fullscreen_row.spacing = (
            20.0
        )

        fullscreen_row.alignment = (
            "center"
        )

        fullscreen_label = fullscreen_row.create_child(
            "FullscreenLabel",
            node_type=Label,
        )

        fullscreen_label.text = (
            "Vollbild"
        )

        fullscreen_label.size = (
            430.0,
            40.0,
        )

        fullscreen_label.pivot = (
            0.5,
            0.5,
        )

        fullscreen_checkbox = fullscreen_row.create_child(
            "FullscreenCheckbox",
            node_type=CheckBox,
        )

        fullscreen_checkbox.size = (
            40.0,
            40.0,
        )

        self._fullscreen_checkbox = (
            fullscreen_checkbox
        )

        # ----------------------------------------------------------
        # VSync row
        # ----------------------------------------------------------

        vsync_row = content.create_child(
            "VSyncRow",
            node_type=HBoxContainer,
        )

        vsync_row.size = (
            600.0,
            50.0,
        )

        vsync_row.spacing = (
            20.0
        )

        vsync_row.alignment = (
            "center"
        )

        vsync_label = vsync_row.create_child(
            "VSyncLabel",
            node_type=Label,
        )

        vsync_label.text = (
            "VSync"
        )

        vsync_label.size = (
            430.0,
            40.0,
        )

        vsync_label.pivot = (
            0.5,
            0.5,
        )

        vsync_checkbox = vsync_row.create_child(
            "VSyncCheckbox",
            node_type=CheckBox,
        )

        vsync_checkbox.size = (
            40.0,
            40.0,
        )

        self._vsync_checkbox = (
            vsync_checkbox
        )

        # ==========================================================
        # AUDIO
        # ==========================================================

        audio_title = content.create_child(
            "AudioTitle",
            node_type=Label,
        )

        audio_title.text = (
            "AUDIO"
        )

        audio_title.scale = (
            1.15
        )

        audio_title.size = (
            600.0,
            40.0,
        )

        audio_title.pivot = (
            0.5,
            0.5,
        )

        # ----------------------------------------------------------
        # Master volume
        # ----------------------------------------------------------

        master_row = content.create_child(
            "MasterRow",
            node_type=HBoxContainer,
        )

        master_row.size = (
            600.0,
            50.0,
        )

        master_row.spacing = (
            15.0
        )

        master_row.alignment = (
            "center"
        )

        master_label = master_row.create_child(
            "MasterLabel",
            node_type=Label,
        )

        master_label.text = (
            "Master"
        )

        master_label.size = (
            130.0,
            40.0,
        )

        master_label.pivot = (
            0.5,
            0.5,
        )

        master_slider = master_row.create_child(
            "MasterSlider",
            node_type=Slider,
        )

        master_slider.size = (
            300.0,
            32.0,
        )

        master_slider.minimum = (
            0.0
        )

        master_slider.maximum = (
            1.0
        )

        self._master_slider = (
            master_slider
        )

        master_value = master_row.create_child(
            "MasterValue",
            node_type=Label,
        )

        master_value.size = (
            90.0,
            40.0,
        )

        master_value.pivot = (
            0.5,
            0.5,
        )

        self._master_value_label = (
            master_value
        )

        # ----------------------------------------------------------
        # Music volume
        # ----------------------------------------------------------

        music_row = content.create_child(
            "MusicRow",
            node_type=HBoxContainer,
        )

        music_row.size = (
            600.0,
            50.0,
        )

        music_row.spacing = (
            15.0
        )

        music_row.alignment = (
            "center"
        )

        music_label = music_row.create_child(
            "MusicLabel",
            node_type=Label,
        )

        music_label.text = (
            "Musik"
        )

        music_label.size = (
            130.0,
            40.0,
        )

        music_label.pivot = (
            0.5,
            0.5,
        )

        music_slider = music_row.create_child(
            "MusicSlider",
            node_type=Slider,
        )

        music_slider.size = (
            300.0,
            32.0,
        )

        music_slider.minimum = (
            0.0
        )

        music_slider.maximum = (
            1.0
        )

        self._music_slider = (
            music_slider
        )

        music_value = music_row.create_child(
            "MusicValue",
            node_type=Label,
        )

        music_value.size = (
            90.0,
            40.0,
        )

        music_value.pivot = (
            0.5,
            0.5,
        )

        self._music_value_label = (
            music_value
        )

        # ----------------------------------------------------------
        # SFX volume
        # ----------------------------------------------------------

        sfx_row = content.create_child(
            "SFXRow",
            node_type=HBoxContainer,
        )

        sfx_row.size = (
            600.0,
            50.0,
        )

        sfx_row.spacing = (
            15.0
        )

        sfx_row.alignment = (
            "center"
        )

        sfx_label = sfx_row.create_child(
            "SFXLabel",
            node_type=Label,
        )

        sfx_label.text = (
            "Effekte"
        )

        sfx_label.size = (
            130.0,
            40.0,
        )

        sfx_label.pivot = (
            0.5,
            0.5,
        )

        sfx_slider = sfx_row.create_child(
            "SFXSlider",
            node_type=Slider,
        )

        sfx_slider.size = (
            300.0,
            32.0,
        )

        sfx_slider.minimum = (
            0.0
        )

        sfx_slider.maximum = (
            1.0
        )

        self._sfx_slider = (
            sfx_slider
        )

        sfx_value = sfx_row.create_child(
            "SFXValue",
            node_type=Label,
        )

        sfx_value.size = (
            90.0,
            40.0,
        )

        sfx_value.pivot = (
            0.5,
            0.5,
        )

        self._sfx_value_label = (
            sfx_value
        )

        # ==========================================================
        # GAMEPLAY
        # ==========================================================

        gameplay_title = content.create_child(
            "GameplayTitle",
            node_type=Label,
        )

        gameplay_title.text = (
            "GAMEPLAY"
        )

        gameplay_title.scale = (
            1.15
        )

        gameplay_title.size = (
            600.0,
            40.0,
        )

        gameplay_title.pivot = (
            0.5,
            0.5,
        )

        gameplay_info = content.create_child(
            "GameplayInfo",
            node_type=Label,
        )

        gameplay_info.text = (
            "Weitere Gameplay-Einstellungen folgen."
        )

        gameplay_info.size = (
            600.0,
            40.0,
        )

        gameplay_info.pivot = (
            0.5,
            0.5,
        )

        # ==========================================================
        # CONTROLS
        # ==========================================================

        controls_title = content.create_child(
            "ControlsTitle",
            node_type=Label,
        )

        controls_title.text = (
            "STEUERUNG"
        )

        controls_title.scale = (
            1.15
        )

        controls_title.size = (
            600.0,
            40.0,
        )

        controls_title.pivot = (
            0.5,
            0.5,
        )

        controls_info = content.create_child(
            "ControlsInfo",
            node_type=Label,
        )

        controls_info.text = (
            "Tastenbelegung folgt später."
        )

        controls_info.size = (
            600.0,
            40.0,
        )

        controls_info.pivot = (
            0.5,
            0.5,
        )

        # ==========================================================
        # FIXED ACTION BUTTONS
        # ==========================================================

        actions = root.create_child(
            "Actions",
            node_type=HBoxContainer,
        )

        actions.size = (
            600.0,
            52.0,
        )

        actions.spacing = (
            20.0
        )

        actions.alignment = (
            "center"
        )

        reset_button = actions.create_child(
            "Reset",
            node_type=Button,
        )

        reset_button.text = (
            "Standardwerte"
        )

        reset_button.size = (
            220.0,
            48.0,
        )

        reset_button.on_click = (
            self._reset
        )

        apply_button = actions.create_child(
            "Apply",
            node_type=Button,
        )

        apply_button.text = (
            "Übernehmen"
        )

        apply_button.size = (
            220.0,
            48.0,
        )

        apply_button.on_click = (
            self._apply
        )

        # ==========================================================
        # Fixed back button
        # ==========================================================

        back_button = root.create_child(
            "Back",
            node_type=Button,
        )

        back_button.text = (
            "Zurück"
        )

        back_button.size = (
            320.0,
            48.0,
        )

        back_button.on_click = (
            self._back
        )

        # ==========================================================
        # Initial state
        # ==========================================================

        self.refresh_from_settings()

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        super().update(
            delta_time
        )

        self._update_value_labels()

    # ==============================================================
    # Refresh from settings
    # ==============================================================

    def refresh_from_settings(
        self,
    ) -> None:
        if (
            self._fullscreen_checkbox
            is not None
        ):
            self._fullscreen_checkbox.checked = (
                bool(
                    self.settings.get(
                        "video.fullscreen",
                        False,
                    )
                )
            )

        if (
            self._vsync_checkbox
            is not None
        ):
            self._vsync_checkbox.checked = (
                bool(
                    self.settings.get(
                        "video.vsync",
                        True,
                    )
                )
            )

        if (
            self._master_slider
            is not None
        ):
            self._master_slider.value = (
                float(
                    self.settings.get(
                        "audio.master_volume",
                        1.0,
                    )
                )
            )

        if (
            self._music_slider
            is not None
        ):
            self._music_slider.value = (
                float(
                    self.settings.get(
                        "audio.music_volume",
                        0.8,
                    )
                )
            )

        if (
            self._sfx_slider
            is not None
        ):
            self._sfx_slider.value = (
                float(
                    self.settings.get(
                        "audio.sfx_volume",
                        0.8,
                    )
                )
            )

        self._update_value_labels()

    # ==============================================================
    # Value labels
    # ==============================================================

    def _update_value_labels(
        self,
    ) -> None:
        if (
            self._master_slider
            is not None
            and self._master_value_label
            is not None
        ):
            value = round(
                self._master_slider.value
                * 100.0
            )

            self._master_value_label.text = (
                f"{value} %"
            )

        if (
            self._music_slider
            is not None
            and self._music_value_label
            is not None
        ):
            value = round(
                self._music_slider.value
                * 100.0
            )

            self._music_value_label.text = (
                f"{value} %"
            )

        if (
            self._sfx_slider
            is not None
            and self._sfx_value_label
            is not None
        ):
            value = round(
                self._sfx_slider.value
                * 100.0
            )

            self._sfx_value_label.text = (
                f"{value} %"
            )

    # ==============================================================
    # Apply
    # ==============================================================

    def _apply(
        self,
    ) -> None:
        # ----------------------------------------------------------
        # Video
        # ----------------------------------------------------------

        if (
            self._fullscreen_checkbox
            is not None
        ):
            self.settings.set(
                "video.fullscreen",
                bool(
                    self._fullscreen_checkbox.checked
                ),
            )

        if (
            self._vsync_checkbox
            is not None
        ):
            self.settings.set(
                "video.vsync",
                bool(
                    self._vsync_checkbox.checked
                ),
            )

        # ----------------------------------------------------------
        # Audio
        # ----------------------------------------------------------

        if (
            self._master_slider
            is not None
        ):
            self.settings.set(
                "audio.master_volume",
                float(
                    self._master_slider.value
                ),
            )

        if (
            self._music_slider
            is not None
        ):
            self.settings.set(
                "audio.music_volume",
                float(
                    self._music_slider.value
                ),
            )

        if (
            self._sfx_slider
            is not None
        ):
            self.settings.set(
                "audio.sfx_volume",
                float(
                    self._sfx_slider.value
                ),
            )

        # ----------------------------------------------------------
        # Save
        # ----------------------------------------------------------

        self.settings.save()

        # ----------------------------------------------------------
        # Apply live
        # ----------------------------------------------------------

        if (
            self._on_apply_callback
            is not None
        ):
            self._on_apply_callback()

        print(
            "[Settings] saved"
        )

    # ==============================================================
    # Reset
    # ==============================================================

    def _reset(
        self,
    ) -> None:
        self.settings.reset(
            save=False
        )

        self.refresh_from_settings()

        print(
            "[Settings] defaults restored"
        )

    # ==============================================================
    # Back
    # ==============================================================

    def _back(
        self,
    ) -> None:
        self.settings.reload()

        self.refresh_from_settings()

        if (
            self._on_back_callback
            is not None
        ):
            self._on_back_callback()