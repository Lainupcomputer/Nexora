from __future__ import annotations

"""DSP effect and preset editing for the audio editor."""

from typing import Callable

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


AUDIO_EFFECT_FACTORIES: dict[str, Callable[[], object]] = {
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


class AudioEffectsMixin:
    def _effect_selected(self, index: int) -> None:
        self._selected_effect = index
        self._sync_controls()

    def _add_effect(self) -> None:
        bus = self._selected_bus()
        factory = AUDIO_EFFECT_FACTORIES.get(self.add_effect_dropdown.value)
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
