from __future__ import annotations

"""Visual editor for Nexora's runtime audio mixer.

Launch with::

    python -m nexora --audioedit

The editor intentionally drives the real :class:`AudioSystem` attached to the
editor Game.  Changes are therefore immediately reflected in the mixer graph,
DSP chains, sends and meters used by the engine.
"""

from pathlib import Path

from nexora.editor.base_editor import EditorBaseScene
from nexora.editor.editors.audio_buses import AudioBusMixin
from nexora.editor.editors.audio_effects import AUDIO_EFFECT_FACTORIES, AudioEffectsMixin
from nexora.editor.editors.audio_rendering import AudioRenderingMixin
from nexora.editor.editors.audio_sends import AudioSendsMixin
from nexora.editor.editors.audio_snapshot import AudioSnapshotMixin
from nexora.editor.model import EditorProjectContext
from nexora.editor.standalone_app import StandaloneEditorApp, run_standalone_editor
from nexora.editor.ui import (
    Button,
    CheckBox,
    Dropdown,
    ListBox,
    Rect,
    Slider,
    TextField,
)


AudioSlider = Slider  # Backward-compatible alias; implementation lives in editor.ui.


class AudioMixerEditorScene(
    AudioBusMixin,
    AudioEffectsMixin,
    AudioSendsMixin,
    AudioSnapshotMixin,
    AudioRenderingMixin,
    EditorBaseScene,
):
    TOOLBAR_HEIGHT = EditorBaseScene.TOOLBAR_HEIGHT
    STATUS_HEIGHT = EditorBaseScene.STATUS_HEIGHT
    LEFT_WIDTH = 260.0
    RIGHT_WIDTH = 390.0
    SNAPSHOT_NAME = "audio_mixer.nmix"

    def __init__(self, game, project_path: Path, project_context: EditorProjectContext | None = None) -> None:
        super().__init__("StandaloneAudioMixerEditor")
        self.game = game
        self.project_context = project_context or EditorProjectContext.from_path(project_path)
        self.project_path = self.project_context.root
        self.status = "Ready"
        self._layout_size = (-1.0, -1.0)
        self._syncing = False
        self._selected_bus_id: str | None = None
        self._selected_effect = -1
        self._selected_send = -1

        self.bus_list = ListBox(Rect(0, 0, 1, 1), self._bus_selected)
        self.effect_list = ListBox(Rect(0, 0, 1, 1), self._effect_selected)
        self.send_list = ListBox(Rect(0, 0, 1, 1), self._send_selected)

        self.add_bus_name = TextField(Rect(0, 0, 1, 1), "", "New bus name")
        self.add_bus_button = Button(Rect(0, 0, 1, 1), "Add Bus", self._add_bus)
        self.remove_bus_button = Button(Rect(0, 0, 1, 1), "Remove", self._remove_bus)
        self.rename_field = TextField(Rect(0, 0, 1, 1), "", "Bus name")
        self.rename_field.on_submit = lambda _value: self._rename_bus()
        self.rename_button = Button(Rect(0, 0, 1, 1), "Rename", self._rename_bus)

        self.parent_dropdown = Dropdown(Rect(0, 0, 1, 1), ("Master",), on_change=self._parent_changed)
        self.volume_slider = Slider(Rect(0, 0, 1, 1), 0.0, 2.0, 1.0, self._volume_changed)
        self.pan_slider = Slider(Rect(0, 0, 1, 1), -1.0, 1.0, 0.0, self._pan_changed)
        self.mute_check = CheckBox(Rect(0, 0, 1, 1), "Mute", False, self._mute_changed)
        self.solo_check = CheckBox(Rect(0, 0, 1, 1), "Solo", False, self._solo_changed)
        self.bypass_chain_check = CheckBox(Rect(0, 0, 1, 1), "Bypass DSP chain", False, self._chain_bypass_changed)
        self.clear_peak_button = Button(Rect(0, 0, 1, 1), "Clear Peak", self._clear_peak)

        effect_names = tuple(AUDIO_EFFECT_FACTORIES)
        self.add_effect_dropdown = Dropdown(Rect(0, 0, 1, 1), effect_names)
        self.add_effect_button = Button(Rect(0, 0, 1, 1), "Add Effect", self._add_effect)
        self.remove_effect_button = Button(Rect(0, 0, 1, 1), "Remove Effect", self._remove_effect)
        self.effect_bypass_check = CheckBox(Rect(0, 0, 1, 1), "Bypass selected", False, self._effect_bypass_changed)
        self.effect_wet_slider = Slider(Rect(0, 0, 1, 1), 0.0, 1.0, 1.0, self._effect_wet_changed)

        preset_names = tuple(preset.name for preset in self.game.audio.get_audio_presets()) or ("Radio",)
        self.preset_dropdown = Dropdown(Rect(0, 0, 1, 1), preset_names)
        self.apply_preset_button = Button(Rect(0, 0, 1, 1), "Apply Preset", self._apply_preset)
        self.append_preset_check = CheckBox(Rect(0, 0, 1, 1), "Append", False)

        self.send_target_dropdown = Dropdown(Rect(0, 0, 1, 1), ("Master",))
        self.send_amount_slider = Slider(Rect(0, 0, 1, 1), 0.0, 2.0, 0.25, self._send_amount_changed)
        self.send_pre_check = CheckBox(Rect(0, 0, 1, 1), "Pre-fader", False, self._send_pre_changed)
        self.add_send_button = Button(Rect(0, 0, 1, 1), "Add Send", self._add_send)
        self.remove_send_button = Button(Rect(0, 0, 1, 1), "Remove Send", self._remove_send)
        self.send_enabled_check = CheckBox(Rect(0, 0, 1, 1), "Enabled", True, self._send_enabled_changed)

        self.effect_parameter_fields = [TextField(Rect(0, 0, 1, 1)) for _ in range(6)]
        self._effect_parameter_names: list[str] = []
        for index, field in enumerate(self.effect_parameter_fields):
            field.on_submit = lambda value, slot=index: self._effect_parameter_submit(slot, value)

        self.save_button = Button(Rect(0, 0, 1, 1), "Save Mixer", self._save_snapshot)
        self.load_button = Button(Rect(0, 0, 1, 1), "Load Mixer", self._load_snapshot)
        self.reset_button = Button(Rect(0, 0, 1, 1), "Reset", self._reset_mixer)

        self._refresh_bus_list(select_name="Master")


    def update(self, delta_time: float) -> None:
        del delta_time
        self._layout()
        mouse_x, mouse_y = self.game.input.mouse_position
        for control in self._controls():
            if control.update(self.game.input, mouse_x, mouse_y):
                break


class AudioMixerEditorApp(StandaloneEditorApp[AudioMixerEditorScene]):
    PROJECT_NAME = "NexoraStandaloneAudioMixerEditor"
    WINDOW_TITLE = "Nexora Audio Mixer"
    WINDOW_WIDTH = 1500
    WINDOW_HEIGHT = 900
    ERROR_PREFIX = "Nexora Audio Mixer"

    def __init__(self, *, project_path: str | Path | None = None) -> None:
        super().__init__(project_path=project_path)
        self.audio_project_path = self.project_path
        self.audio_project_context = self.project_context

    def create_editor_scene(self) -> AudioMixerEditorScene:
        return AudioMixerEditorScene(
            self,
            self.project_path,
            self.project_context,
        )


def run_audio_mixer_editor(project_path: str | Path | None = None) -> int:
    return run_standalone_editor(AudioMixerEditorApp, project_path=project_path)


__all__ = ["AudioMixerEditorApp", "AudioMixerEditorScene", "AudioSlider", "run_audio_mixer_editor"]
