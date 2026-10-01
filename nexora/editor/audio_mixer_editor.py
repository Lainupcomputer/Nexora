from __future__ import annotations

"""Standalone visual editor for Nexora's runtime audio mixer.

Launch with::

    python -m nexora --audioedit

The editor intentionally drives the real :class:`AudioSystem` attached to the
editor Game.  Changes are therefore immediately reflected in the mixer graph,
DSP chains, sends and meters used by the engine.
"""

import json
import math
from pathlib import Path
from typing import Callable

from nexora import Game
from nexora.audio import (
    CompressorEffect,
    DelayEffect,
    DistortionEffect,
    GainEffect,
    HighPassFilterEffect,
    LimiterEffect,
    LowPassFilterEffect,
    NoiseGateEffect,
    ParametricEQEffect,
    ReverbEffect,
    StereoWidthEffect,
)
from nexora.editor.app import resolve_project_path
from nexora.editor.model import EditorProjectContext
from nexora.editor.ui import (
    Button,
    CheckBox,
    Control,
    Dropdown,
    ListBox,
    Rect,
    TextField,
    UITheme,
    draw_outline,
    draw_rect,
    draw_text,
)
from nexora.scene import Scene


_EFFECT_FACTORIES: dict[str, Callable[[], object]] = {
    "Gain": GainEffect,
    "Limiter": LimiterEffect,
    "Low-pass": LowPassFilterEffect,
    "High-pass": HighPassFilterEffect,
    "Parametric EQ": ParametricEQEffect,
    "Compressor": CompressorEffect,
    "Delay": DelayEffect,
    "Reverb": ReverbEffect,
    "Distortion": DistortionEffect,
    "Noise Gate": NoiseGateEffect,
    "Stereo Width": StereoWidthEffect,
}


def _dbfs_label(value: float) -> str:
    if not math.isfinite(value):
        return "-inf"
    return f"{value:.1f} dB"


class AudioSlider(Control):
    """Small local slider so the mixer editor does not expand shared UI API."""

    def __init__(
        self,
        rect: Rect,
        minimum: float,
        maximum: float,
        value: float,
        on_change: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(rect)
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self._value = float(value)
        self.on_change = on_change
        self.dragging = False
        self.value = value

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._value = max(self.minimum, min(self.maximum, float(value)))

    def update(self, input_manager, mouse_x: float, mouse_y: float) -> bool:
        super().update(input_manager, mouse_x, mouse_y)
        if self.enabled and self.hovered and input_manager.mouse_pressed("left"):
            self.dragging = True
        if self.dragging and not input_manager.mouse_down("left"):
            self.dragging = False
        if not self.dragging:
            return False
        fraction = (float(mouse_x) - self.rect.x) / max(1.0, self.rect.width)
        self.value = self.minimum + max(0.0, min(1.0, fraction)) * (self.maximum - self.minimum)
        if self.on_change is not None:
            self.on_change(self.value)
        return True

    def render(self, renderer, viewport, theme: UITheme) -> None:
        draw_rect(renderer, self.rect, theme.input, viewport, radius=4.0)
        draw_outline(renderer, self.rect, theme.accent if self.dragging else theme.border, viewport)
        fraction = (self.value - self.minimum) / max(1e-9, self.maximum - self.minimum)
        fill = Rect(self.rect.x + 2.0, self.rect.y + 2.0, max(0.0, (self.rect.width - 4.0) * fraction), self.rect.height - 4.0)
        if fill.width > 0.0:
            draw_rect(renderer, fill, theme.accent, viewport, radius=3.0)


class AudioMixerEditorScene(Scene):
    TOOLBAR_HEIGHT = 56.0
    STATUS_HEIGHT = 28.0
    LEFT_WIDTH = 260.0
    RIGHT_WIDTH = 390.0
    SNAPSHOT_NAME = "audio_mixer.json"

    def __init__(self, game, project_path: Path, project_context: EditorProjectContext | None = None) -> None:
        super().__init__("StandaloneAudioMixerEditor")
        self.game = game
        self.project_context = project_context or EditorProjectContext.from_path(project_path)
        self.project_path = self.project_context.root
        self.theme = UITheme()
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
        self.volume_slider = AudioSlider(Rect(0, 0, 1, 1), 0.0, 2.0, 1.0, self._volume_changed)
        self.pan_slider = AudioSlider(Rect(0, 0, 1, 1), -1.0, 1.0, 0.0, self._pan_changed)
        self.mute_check = CheckBox(Rect(0, 0, 1, 1), "Mute", False, self._mute_changed)
        self.solo_check = CheckBox(Rect(0, 0, 1, 1), "Solo", False, self._solo_changed)
        self.bypass_chain_check = CheckBox(Rect(0, 0, 1, 1), "Bypass DSP chain", False, self._chain_bypass_changed)
        self.clear_peak_button = Button(Rect(0, 0, 1, 1), "Clear Peak", self._clear_peak)

        effect_names = tuple(_EFFECT_FACTORIES)
        self.add_effect_dropdown = Dropdown(Rect(0, 0, 1, 1), effect_names)
        self.add_effect_button = Button(Rect(0, 0, 1, 1), "Add Effect", self._add_effect)
        self.remove_effect_button = Button(Rect(0, 0, 1, 1), "Remove Effect", self._remove_effect)
        self.effect_bypass_check = CheckBox(Rect(0, 0, 1, 1), "Bypass selected", False, self._effect_bypass_changed)
        self.effect_wet_slider = AudioSlider(Rect(0, 0, 1, 1), 0.0, 1.0, 1.0, self._effect_wet_changed)

        preset_names = tuple(preset.name for preset in self.game.audio.get_audio_presets()) or ("Radio",)
        self.preset_dropdown = Dropdown(Rect(0, 0, 1, 1), preset_names)
        self.apply_preset_button = Button(Rect(0, 0, 1, 1), "Apply Preset", self._apply_preset)
        self.append_preset_check = CheckBox(Rect(0, 0, 1, 1), "Append", False)

        self.send_target_dropdown = Dropdown(Rect(0, 0, 1, 1), ("Master",))
        self.send_amount_slider = AudioSlider(Rect(0, 0, 1, 1), 0.0, 2.0, 0.25, self._send_amount_changed)
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

    @property
    def snapshot_path(self) -> Path:
        return self.project_path / self.SNAPSHOT_NAME

    def _selected_bus(self):
        if self._selected_bus_id is None:
            return None
        try:
            return self.game.audio.get_bus_by_id(self._selected_bus_id)
        except KeyError:
            return None

    def _refresh_bus_list(self, *, select_name: str | None = None) -> None:
        buses = self.game.audio.get_buses()
        items = []
        selected_index = -1
        for index, bus in enumerate(buses):
            parent = bus.parent.name if bus.parent is not None else "—"
            prefix = "◆" if bus.name.casefold() == "master" else "•"
            items.append(f"{prefix} {bus.name}  →  {parent}")
            if (select_name and bus.name.casefold() == select_name.casefold()) or bus.id == self._selected_bus_id:
                selected_index = index
        self.bus_list.set_items(items)
        if selected_index < 0 and buses:
            selected_index = 0
        if selected_index >= 0:
            self.bus_list.selected = selected_index
            self._selected_bus_id = buses[selected_index].id
        self._sync_controls()

    def _sync_controls(self) -> None:
        bus = self._selected_bus()
        if bus is None:
            return
        self._syncing = True
        try:
            self.rename_field.set_text(bus.name)
            self.volume_slider.value = bus.volume
            self.pan_slider.value = bus.pan
            self.mute_check.checked = bus.muted
            self.solo_check.checked = bus.solo
            self.bypass_chain_check.checked = bus.effects_bypassed
            parents = [candidate.name for candidate in self.game.audio.get_buses() if candidate is not bus]
            if bus.name.casefold() == "master":
                parents = ["—"]
            elif "Master" not in parents:
                parents.insert(0, "Master")
            self.parent_dropdown.options = tuple(parents or ["—"])
            parent_name = bus.parent.name if bus.parent is not None else "Master"
            if bus.name.casefold() == "master":
                parent_name = "—"
            try:
                self.parent_dropdown.selected = self.parent_dropdown.options.index(parent_name)
            except ValueError:
                self.parent_dropdown.selected = 0

            self.effect_list.set_items([
                f"{index + 1}. {type(effect).__name__}  wet {effect.wet:.0%}{'  [BYPASS]' if effect.bypassed else ''}"
                for index, effect in enumerate(bus.effects)
            ])
            if self._selected_effect >= len(bus.effects):
                self._selected_effect = len(bus.effects) - 1
            self.effect_list.selected = self._selected_effect
            effect = bus.effects[self._selected_effect] if 0 <= self._selected_effect < len(bus.effects) else None
            self.effect_bypass_check.checked = bool(effect.bypassed) if effect is not None else False
            self.effect_wet_slider.value = effect.wet if effect is not None else 1.0
            self.effect_bypass_check.enabled = effect is not None
            self.effect_wet_slider.enabled = effect is not None
            self.remove_effect_button.enabled = effect is not None
            self._effect_parameter_names = []
            parameter_values = {} if effect is None else dict(effect.to_state().get("parameters") or {})
            for slot, field in enumerate(self.effect_parameter_fields):
                if slot < len(parameter_values):
                    parameter, value = list(parameter_values.items())[slot]
                    self._effect_parameter_names.append(parameter)
                    field.set_text(str(value))
                    field.enabled = True
                    field.visible = True
                else:
                    field.set_text("")
                    field.enabled = False
                    field.visible = False

            sends = self.game.audio.mixer.get_sends_from(bus)
            send_items = []
            for send in sends:
                target = self.game.audio.get_bus_by_id(send.target_bus_id)
                mode = "pre" if send.pre_fader else "post"
                send_items.append(f"{target.name}  {send.amount:.2f}  {mode}{'' if send.enabled else ' [off]'}")
            self.send_list.set_items(send_items)
            if self._selected_send >= len(sends):
                self._selected_send = len(sends) - 1
            self.send_list.selected = self._selected_send
            selected_send = sends[self._selected_send] if 0 <= self._selected_send < len(sends) else None
            self.send_enabled_check.enabled = selected_send is not None
            self.remove_send_button.enabled = selected_send is not None
            if selected_send is not None:
                self.send_enabled_check.checked = selected_send.enabled
                self.send_amount_slider.value = selected_send.amount
                self.send_pre_check.checked = selected_send.pre_fader

            targets = [candidate.name for candidate in self.game.audio.get_buses() if candidate is not bus]
            self.send_target_dropdown.options = tuple(targets or ["Master"])
            self.send_target_dropdown.selected = min(self.send_target_dropdown.selected, len(self.send_target_dropdown.options) - 1)
            self.remove_bus_button.enabled = bus.name.casefold() != "master"
            self.rename_button.enabled = bus.name.casefold() != "master"
            self.rename_field.enabled = bus.name.casefold() != "master"
            self.parent_dropdown.enabled = bus.name.casefold() != "master"
        finally:
            self._syncing = False

    def _bus_selected(self, index: int) -> None:
        buses = self.game.audio.get_buses()
        if 0 <= index < len(buses):
            self._selected_bus_id = buses[index].id
            self._selected_effect = -1
            self._selected_send = -1
            self._sync_controls()

    def _effect_selected(self, index: int) -> None:
        self._selected_effect = index
        self._sync_controls()

    def _send_selected(self, index: int) -> None:
        self._selected_send = index
        self._sync_controls()

    def _add_bus(self) -> None:
        name = self.add_bus_name.text.strip()
        if not name:
            self.status = "Enter a bus name."
            return
        try:
            parent = self._selected_bus() or self.game.audio.mixer.master
            self.game.audio.create_bus(name, parent=parent)
            self.add_bus_name.set_text("")
            self.status = f"Created bus {name}."
            self._refresh_bus_list(select_name=name)
        except Exception as exc:
            self.status = f"Bus error: {exc}"

    def _remove_bus(self) -> None:
        bus = self._selected_bus()
        if bus is None or bus.name.casefold() == "master":
            return
        name = bus.name
        try:
            parent = bus.parent.name if bus.parent is not None else "Master"
            self.game.audio.remove_bus(name, reassign_to=parent, reparent_children=True)
            self._selected_bus_id = None
            self.status = f"Removed bus {name}."
            self._refresh_bus_list(select_name=parent)
        except Exception as exc:
            self.status = f"Remove failed: {exc}"

    def _rename_bus(self) -> None:
        bus = self._selected_bus()
        if bus is None or bus.name.casefold() == "master":
            return
        new_name = self.rename_field.text.strip()
        if not new_name:
            return
        try:
            self.game.audio.rename_bus(bus.id, new_name)
            self.status = f"Renamed bus to {new_name}."
            self._refresh_bus_list(select_name=new_name)
        except Exception as exc:
            self.status = f"Rename failed: {exc}"

    def _parent_changed(self, _index: int, value: str) -> None:
        if self._syncing:
            return
        bus = self._selected_bus()
        if bus is None or bus.name.casefold() == "master":
            return
        try:
            self.game.audio.set_bus_parent(bus.name, value)
            self.status = f"{bus.name} → {value}"
            self._refresh_bus_list(select_name=bus.name)
        except Exception as exc:
            self.status = f"Routing rejected: {exc}"
            self._sync_controls()

    def _volume_changed(self, value: float) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.volume = value

    def _pan_changed(self, value: float) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.pan = value

    def _mute_changed(self, value: bool) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.muted = value

    def _solo_changed(self, value: bool) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.solo = value

    def _chain_bypass_changed(self, value: bool) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.effects_bypassed = value

    def _clear_peak(self) -> None:
        bus = self._selected_bus()
        if bus is not None:
            bus.clear_peak_hold()

    def _add_effect(self) -> None:
        bus = self._selected_bus()
        factory = _EFFECT_FACTORIES.get(self.add_effect_dropdown.value)
        if bus is None or factory is None:
            return
        try:
            bus.add_effect(factory())
            self._selected_effect = len(bus.effects) - 1
            self.status = f"Added {self.add_effect_dropdown.value}."
            self._sync_controls()
        except Exception as exc:
            self.status = f"Effect error: {exc}"

    def _remove_effect(self) -> None:
        bus = self._selected_bus()
        if bus is None or not (0 <= self._selected_effect < len(bus.effects)):
            return
        effect = bus.effects[self._selected_effect]
        bus.remove_effect(effect)
        self._selected_effect = min(self._selected_effect, len(bus.effects) - 1)
        self.status = f"Removed {type(effect).__name__}."
        self._sync_controls()

    def _effect_bypass_changed(self, value: bool) -> None:
        bus = self._selected_bus()
        if bus is not None and 0 <= self._selected_effect < len(bus.effects) and not self._syncing:
            bus.effects[self._selected_effect].bypassed = value
            self._sync_controls()

    def _effect_wet_changed(self, value: float) -> None:
        bus = self._selected_bus()
        if bus is not None and 0 <= self._selected_effect < len(bus.effects) and not self._syncing:
            bus.effects[self._selected_effect].wet = value

    def _apply_preset(self) -> None:
        bus = self._selected_bus()
        if bus is None:
            return
        try:
            self.game.audio.apply_audio_preset(
                self.preset_dropdown.value,
                bus,
                replace=not self.append_preset_check.checked,
            )
            self.status = f"Applied {self.preset_dropdown.value} to {bus.name}."
            self._selected_effect = -1
            self._sync_controls()
        except Exception as exc:
            self.status = f"Preset error: {exc}"

    def _add_send(self) -> None:
        bus = self._selected_bus()
        if bus is None or not self.send_target_dropdown.value:
            return
        try:
            self.game.audio.add_send(
                bus,
                self.send_target_dropdown.value,
                amount=self.send_amount_slider.value,
                pre_fader=self.send_pre_check.checked,
            )
            self.status = f"Added send {bus.name} → {self.send_target_dropdown.value}."
            self._selected_send = -1
            self._sync_controls()
        except Exception as exc:
            self.status = f"Send rejected: {exc}"

    def _remove_send(self) -> None:
        bus = self._selected_bus()
        if bus is None:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if not (0 <= self._selected_send < len(sends)):
            return
        self.game.audio.remove_send(sends[self._selected_send])
        self._selected_send = -1
        self.status = "Removed send."
        self._sync_controls()

    def _send_enabled_changed(self, enabled: bool) -> None:
        bus = self._selected_bus()
        if bus is None or self._syncing:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if 0 <= self._selected_send < len(sends):
            try:
                self.game.audio.set_send_enabled(sends[self._selected_send].id, enabled)
            except Exception as exc:
                self.status = f"Send rejected: {exc}"
                self._sync_controls()

    def _send_amount_changed(self, amount: float) -> None:
        bus = self._selected_bus()
        if bus is None or self._syncing:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if 0 <= self._selected_send < len(sends):
            self.game.audio.set_send_amount(sends[self._selected_send].id, amount)

    def _send_pre_changed(self, pre_fader: bool) -> None:
        bus = self._selected_bus()
        if bus is None or self._syncing:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if 0 <= self._selected_send < len(sends):
            self.game.audio.set_send_pre_fader(sends[self._selected_send].id, pre_fader)
            self._sync_controls()

    def _effect_parameter_submit(self, slot: int, value: str) -> None:
        bus = self._selected_bus()
        if bus is None or not (0 <= self._selected_effect < len(bus.effects)):
            return
        if not (0 <= slot < len(self._effect_parameter_names)):
            return
        parameter = self._effect_parameter_names[slot]
        effect = bus.effects[self._selected_effect]
        current = effect.get_parameter(parameter)
        try:
            if isinstance(current, bool):
                parsed = value.strip().casefold() in {"1", "true", "yes", "on"}
            elif isinstance(current, int) and not isinstance(current, bool):
                parsed = int(value)
            elif isinstance(current, float):
                parsed = float(value)
            else:
                parsed = value
            effect.set_parameter(parameter, parsed)
            self.status = f"{parameter} = {parsed}"
            self._sync_controls()
        except Exception as exc:
            self.status = f"Parameter error: {exc}"
            self._sync_controls()

    def _save_snapshot(self) -> None:
        try:
            self.snapshot_path.write_text(
                json.dumps(self.game.audio.create_mixer_snapshot(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self.status = f"Saved {self.snapshot_path.name}."
        except Exception as exc:
            self.status = f"Save failed: {exc}"

    def _load_snapshot(self) -> None:
        try:
            data = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            self.game.audio.restore_mixer_snapshot(data)
            self._selected_bus_id = None
            self._selected_effect = -1
            self._selected_send = -1
            self._refresh_bus_list(select_name="Master")
            self.status = f"Loaded {self.snapshot_path.name}."
        except FileNotFoundError:
            self.status = f"{self.snapshot_path.name} does not exist yet."
        except Exception as exc:
            self.status = f"Load failed: {exc}"

    def _reset_mixer(self) -> None:
        self.game.audio.reset()
        self.status = "Mixer reset."
        self._sync_controls()

    def _layout(self) -> tuple[float, float]:
        width = float(self.game.window.width)
        height = float(self.game.window.height)
        if (width, height) == self._layout_size:
            return width, height
        self._layout_size = (width, height)

        left = 10.0
        top = self.TOOLBAR_HEIGHT + 10.0
        bottom = height - self.STATUS_HEIGHT - 10.0
        left_panel_w = self.LEFT_WIDTH
        right_x = width - self.RIGHT_WIDTH - 10.0
        center_x = left + left_panel_w + 10.0
        center_w = max(360.0, right_x - center_x - 10.0)

        self.bus_list.rect = Rect(left, top + 34.0, left_panel_w, max(180.0, bottom - top - 126.0))
        self.add_bus_name.rect = Rect(left, bottom - 78.0, left_panel_w - 92.0, 32.0)
        self.add_bus_button.rect = Rect(left + left_panel_w - 84.0, bottom - 78.0, 84.0, 32.0)
        self.remove_bus_button.rect = Rect(left, bottom - 38.0, left_panel_w, 32.0)

        cx = center_x + 14.0
        field_w = min(360.0, center_w - 28.0)
        self.rename_field.rect = Rect(cx, top + 42.0, field_w - 92.0, 32.0)
        self.rename_button.rect = Rect(cx + field_w - 84.0, top + 42.0, 84.0, 32.0)
        self.parent_dropdown.rect = Rect(cx, top + 104.0, field_w, 32.0)
        self.volume_slider.rect = Rect(cx, top + 176.0, field_w, 24.0)
        self.pan_slider.rect = Rect(cx, top + 238.0, field_w, 24.0)
        self.mute_check.rect = Rect(cx, top + 280.0, 90.0, 28.0)
        self.solo_check.rect = Rect(cx + 100.0, top + 280.0, 90.0, 28.0)
        self.bypass_chain_check.rect = Rect(cx + 200.0, top + 280.0, 180.0, 28.0)
        self.clear_peak_button.rect = Rect(cx, top + 394.0, 120.0, 30.0)
        for index, field in enumerate(self.effect_parameter_fields):
            column = index % 2
            row = index // 2
            field.rect = Rect(cx + column * 188.0, top + 484.0 + row * 58.0, 174.0, 32.0)

        rx = right_x + 12.0
        rw = self.RIGHT_WIDTH - 24.0
        self.preset_dropdown.rect = Rect(rx, top + 36.0, rw - 128.0, 32.0)
        self.apply_preset_button.rect = Rect(rx + rw - 120.0, top + 36.0, 120.0, 32.0)
        self.append_preset_check.rect = Rect(rx, top + 74.0, 110.0, 26.0)

        self.effect_list.rect = Rect(rx, top + 130.0, rw, 160.0)
        self.add_effect_dropdown.rect = Rect(rx, top + 300.0, rw - 120.0, 32.0)
        self.add_effect_button.rect = Rect(rx + rw - 112.0, top + 300.0, 112.0, 32.0)
        self.remove_effect_button.rect = Rect(rx, top + 338.0, 136.0, 30.0)
        self.effect_bypass_check.rect = Rect(rx + 148.0, top + 340.0, 160.0, 28.0)
        self.effect_wet_slider.rect = Rect(rx, top + 398.0, rw, 22.0)

        self.send_list.rect = Rect(rx, top + 466.0, rw, 122.0)
        self.send_target_dropdown.rect = Rect(rx, top + 598.0, rw - 110.0, 32.0)
        self.add_send_button.rect = Rect(rx + rw - 102.0, top + 598.0, 102.0, 32.0)
        self.send_amount_slider.rect = Rect(rx, top + 652.0, rw, 22.0)
        self.send_pre_check.rect = Rect(rx, top + 684.0, 126.0, 28.0)
        self.send_enabled_check.rect = Rect(rx + 132.0, top + 684.0, 110.0, 28.0)
        self.remove_send_button.rect = Rect(rx + rw - 122.0, top + 682.0, 122.0, 30.0)

        self.save_button.rect = Rect(10.0, 12.0, 118.0, 32.0)
        self.load_button.rect = Rect(136.0, 12.0, 118.0, 32.0)
        self.reset_button.rect = Rect(262.0, 12.0, 92.0, 32.0)
        return width, height

    def _controls(self) -> list[Control]:
        return [
            self.bus_list,
            self.add_bus_name,
            self.add_bus_button,
            self.remove_bus_button,
            self.rename_field,
            self.rename_button,
            self.parent_dropdown,
            self.volume_slider,
            self.pan_slider,
            self.mute_check,
            self.solo_check,
            self.bypass_chain_check,
            self.clear_peak_button,
            self.preset_dropdown,
            self.apply_preset_button,
            self.append_preset_check,
            self.effect_list,
            self.add_effect_dropdown,
            self.add_effect_button,
            self.remove_effect_button,
            self.effect_bypass_check,
            self.effect_wet_slider,
            *self.effect_parameter_fields,
            self.send_list,
            self.send_target_dropdown,
            self.add_send_button,
            self.send_amount_slider,
            self.send_pre_check,
            self.send_enabled_check,
            self.remove_send_button,
            self.save_button,
            self.load_button,
            self.reset_button,
        ]

    def update(self, delta_time: float) -> None:
        del delta_time
        self._layout()
        mouse_x, mouse_y = self.game.input.mouse_position
        for control in self._controls():
            if control.update(self.game.input, mouse_x, mouse_y):
                break

    def _draw_meter(self, renderer, viewport: tuple[float, float], rect: Rect, value: float, peak: float, clipped: bool) -> None:
        draw_rect(renderer, rect, self.theme.input, viewport, radius=3.0)
        draw_outline(renderer, rect, self.theme.border, viewport)
        fraction = max(0.0, min(1.0, float(value)))
        fill = Rect(rect.x + 2.0, rect.y + 2.0, (rect.width - 4.0) * fraction, rect.height - 4.0)
        if fill.width > 0:
            draw_rect(renderer, fill, self.theme.error if clipped else self.theme.accent, viewport, radius=2.0)
        hold_x = rect.x + 2.0 + (rect.width - 4.0) * max(0.0, min(1.0, peak))
        draw_rect(renderer, Rect(hold_x, rect.y + 1.0, 2.0, rect.height - 2.0), self.theme.warning, viewport)

    def render(self, interpolation: float) -> None:
        del interpolation
        width, height = self._layout()
        viewport = (width, height)
        renderer = self.game.renderer
        draw_rect(renderer, Rect(0, 0, width, height), self.theme.background, viewport)
        with renderer.overlay_scope():
            draw_rect(renderer, Rect(0, 0, width, self.TOOLBAR_HEIGHT), self.theme.panel, viewport)
            draw_rect(renderer, Rect(0, height - self.STATUS_HEIGHT, width, self.STATUS_HEIGHT), self.theme.panel, viewport)
            draw_rect(renderer, Rect(10, self.TOOLBAR_HEIGHT + 10, self.LEFT_WIDTH, height - self.TOOLBAR_HEIGHT - self.STATUS_HEIGHT - 20), self.theme.panel, viewport)
            draw_rect(renderer, Rect(width - self.RIGHT_WIDTH - 10, self.TOOLBAR_HEIGHT + 10, self.RIGHT_WIDTH, height - self.TOOLBAR_HEIGHT - self.STATUS_HEIGHT - 20), self.theme.panel, viewport)

            for button in (self.save_button, self.load_button, self.reset_button):
                button.render(renderer, viewport, self.theme)
            draw_text(renderer, "Nexora Audio Mixer", width - 18.0, 17.0, viewport, scale=0.70, align="right")
            draw_text(renderer, "Buses", 20.0, self.TOOLBAR_HEIGHT + 18.0, viewport, scale=0.72)
            self.bus_list.render(renderer, viewport, self.theme)
            self.add_bus_name.render(renderer, viewport, self.theme)
            self.add_bus_button.render(renderer, viewport, self.theme)
            self.remove_bus_button.render(renderer, viewport, self.theme)

            bus = self._selected_bus()
            center_x = self.LEFT_WIDTH + 34.0
            if bus is not None:
                draw_text(renderer, bus.name, center_x, self.TOOLBAR_HEIGHT + 22.0, viewport, scale=0.92)
                draw_text(renderer, f"ID {bus.id[:12]}", center_x, self.TOOLBAR_HEIGHT + 58.0, viewport, scale=0.46, color=self.theme.muted)
                draw_text(renderer, "Parent", center_x, self.TOOLBAR_HEIGHT + 94.0, viewport, scale=0.48, color=self.theme.muted)
                draw_text(renderer, f"Volume  {bus.volume:.2f}", center_x, self.TOOLBAR_HEIGHT + 158.0, viewport, scale=0.50)
                draw_text(renderer, f"Pan  {bus.pan:+.2f}", center_x, self.TOOLBAR_HEIGHT + 220.0, viewport, scale=0.50)
                self.rename_field.render(renderer, viewport, self.theme)
                self.rename_button.render(renderer, viewport, self.theme)
                self.parent_dropdown.render(renderer, viewport, self.theme)
                self.volume_slider.render(renderer, viewport, self.theme)
                self.pan_slider.render(renderer, viewport, self.theme)
                self.mute_check.render(renderer, viewport, self.theme)
                self.solo_check.render(renderer, viewport, self.theme)
                self.bypass_chain_check.render(renderer, viewport, self.theme)

                peak_l, peak_r = bus.peak
                hold_l, hold_r = bus.peak_hold
                peak_db_l, peak_db_r = bus.peak_dbfs
                meter_y = self.TOOLBAR_HEIGHT + 335.0
                draw_text(renderer, "Meter L", center_x, meter_y - 20.0, viewport, scale=0.46, color=self.theme.muted)
                self._draw_meter(renderer, viewport, Rect(center_x, meter_y, 300.0, 18.0), peak_l, hold_l, bus.clipped)
                draw_text(renderer, _dbfs_label(peak_db_l), center_x + 310.0, meter_y - 1.0, viewport, scale=0.42, color=self.theme.muted)
                draw_text(renderer, "Meter R", center_x, meter_y + 26.0, viewport, scale=0.46, color=self.theme.muted)
                self._draw_meter(renderer, viewport, Rect(center_x, meter_y + 46.0, 300.0, 18.0), peak_r, hold_r, bus.clipped)
                draw_text(renderer, _dbfs_label(peak_db_r), center_x + 310.0, meter_y + 45.0, viewport, scale=0.42, color=self.theme.muted)
                self.clear_peak_button.render(renderer, viewport, self.theme)
                if self._effect_parameter_names:
                    draw_text(renderer, "Selected effect parameters", center_x, self.TOOLBAR_HEIGHT + 454.0, viewport, scale=0.54)
                    for index, parameter in enumerate(self._effect_parameter_names):
                        field = self.effect_parameter_fields[index]
                        draw_text(renderer, parameter, field.rect.x, field.rect.y - 18.0, viewport, scale=0.42, color=self.theme.muted)
                        field.render(renderer, viewport, self.theme)

            right_x = width - self.RIGHT_WIDTH
            draw_text(renderer, "Preset", right_x + 14.0, self.TOOLBAR_HEIGHT + 18.0, viewport, scale=0.62)
            self.preset_dropdown.render(renderer, viewport, self.theme)
            self.apply_preset_button.render(renderer, viewport, self.theme)
            self.append_preset_check.render(renderer, viewport, self.theme)
            draw_text(renderer, "DSP Effects", right_x + 14.0, self.TOOLBAR_HEIGHT + 112.0, viewport, scale=0.62)
            self.effect_list.render(renderer, viewport, self.theme)
            self.add_effect_dropdown.render(renderer, viewport, self.theme)
            self.add_effect_button.render(renderer, viewport, self.theme)
            self.remove_effect_button.render(renderer, viewport, self.theme)
            self.effect_bypass_check.render(renderer, viewport, self.theme)
            draw_text(renderer, f"Wet {self.effect_wet_slider.value:.0%}", right_x + 14.0, self.TOOLBAR_HEIGHT + 382.0, viewport, scale=0.46, color=self.theme.muted)
            self.effect_wet_slider.render(renderer, viewport, self.theme)

            draw_text(renderer, "Sends", right_x + 14.0, self.TOOLBAR_HEIGHT + 446.0, viewport, scale=0.62)
            self.send_list.render(renderer, viewport, self.theme)
            self.send_target_dropdown.render(renderer, viewport, self.theme)
            self.add_send_button.render(renderer, viewport, self.theme)
            draw_text(renderer, f"Amount {self.send_amount_slider.value:.2f}", right_x + 14.0, self.TOOLBAR_HEIGHT + 636.0, viewport, scale=0.46, color=self.theme.muted)
            self.send_amount_slider.render(renderer, viewport, self.theme)
            self.send_pre_check.render(renderer, viewport, self.theme)
            self.send_enabled_check.render(renderer, viewport, self.theme)
            self.remove_send_button.render(renderer, viewport, self.theme)

            draw_text(renderer, self.status, 12.0, height - self.STATUS_HEIGHT + 6.0, viewport, scale=0.50, color=self.theme.muted)
            draw_text(renderer, str(self.snapshot_path), width - 12.0, height - self.STATUS_HEIGHT + 6.0, viewport, scale=0.43, color=self.theme.muted, align="right")


class AudioMixerEditorApp(Game):
    def __init__(self, *, project_path: str | Path | None = None) -> None:
        self.audio_project_path = resolve_project_path(project_path)
        self.audio_project_context = EditorProjectContext.from_path(self.audio_project_path)
        super().__init__(
            project_name="NexoraStandaloneAudioMixerEditor",
            title=f"Nexora Audio Mixer - {self.audio_project_path.name}",
            width=1500,
            height=900,
            resizable=True,
            editor_mode=True,
        )
        self.editor_scene = None

    def initialize(self) -> None:
        if self.engine is not None:
            self.engine.assets.root = self.audio_project_context.assets_root
        icon_path = self.audio_project_context.icon_path
        if self.window is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                pass
        self.editor_scene = AudioMixerEditorScene(
            self,
            self.audio_project_path,
            self.audio_project_context,
        )
        self.scene = self.editor_scene


def run_audio_mixer_editor(project_path: str | Path | None = None) -> int:
    try:
        AudioMixerEditorApp(project_path=project_path).run()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[Nexora Audio Mixer] {exc}")
        return 2
    return 0


__all__ = ["AudioMixerEditorApp", "AudioMixerEditorScene", "AudioSlider", "run_audio_mixer_editor"]
