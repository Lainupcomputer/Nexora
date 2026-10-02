from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Iterable

from nexora.data.codecs import audio_preset as audio_preset_codec

from .bus import AudioBus
from .effects import (
    AudioEffect,
    CompressorEffect,
    DelayEffect,
    DistortionEffect,
    HighPassFilterEffect,
    LowPassFilterEffect,
    NoiseGateEffect,
    ParametricEQEffect,
    ReverbEffect,
    StereoWidthEffect,
    audio_effect_from_state,
)


def _normalize_name(name: str) -> str:
    value = str(name).strip()
    if not value:
        raise ValueError("Audio preset name must not be empty.")
    return value


@dataclass(frozen=True, slots=True)
class AudioPreset:
    """Serializable named DSP effect chain.

    Presets store effect configuration, never live effect objects. Applying a
    preset therefore creates fresh stateful DSP instances for the destination
    bus so delay/reverb/filter state cannot leak between buses.
    """

    name: str
    effects: tuple[dict, ...]
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalize_name(self.name))
        object.__setattr__(self, "description", str(self.description).strip())
        object.__setattr__(
            self,
            "effects",
            tuple(copy.deepcopy(effect_state) for effect_state in self.effects),
        )

    @classmethod
    def from_effects(
        cls,
        name: str,
        effects: Iterable[AudioEffect],
        *,
        description: str = "",
    ) -> "AudioPreset":
        return cls(
            name=_normalize_name(name),
            description=description,
            effects=tuple(effect.to_state() for effect in effects),
        )

    @classmethod
    def from_bus(
        cls,
        name: str,
        bus: AudioBus,
        *,
        description: str = "",
    ) -> "AudioPreset":
        return cls.from_effects(name, bus.effects, description=description)

    def instantiate_effects(self) -> tuple[AudioEffect, ...]:
        return tuple(audio_effect_from_state(state) for state in self.effects)

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "name": self.name,
            "description": self.description,
            "effects": [copy.deepcopy(state) for state in self.effects],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AudioPreset":
        if not isinstance(data, dict):
            raise TypeError("Audio preset data must be a dictionary.")
        version = int(data.get("version", 1))
        if version != 1:
            raise ValueError(f"Unsupported audio preset version: {version}")
        effects = data.get("effects")
        if not isinstance(effects, list):
            raise ValueError("Audio preset must contain an effects list.")
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            effects=tuple(copy.deepcopy(state) for state in effects),
        )


class AudioPresetRegistry:
    """Thread-safe registry for built-in and user-defined DSP presets."""

    def __init__(self, *, include_builtins: bool = True) -> None:
        self._lock = RLock()
        self._presets: dict[str, AudioPreset] = {}
        if include_builtins:
            for preset in create_builtin_presets():
                self.register(preset)

    def register(
        self,
        preset: AudioPreset,
        *,
        overwrite: bool = False,
    ) -> AudioPreset:
        if not isinstance(preset, AudioPreset):
            raise TypeError("preset must be an AudioPreset.")
        key = preset.name.casefold()
        with self._lock:
            if key in self._presets and not overwrite:
                raise ValueError(f"Audio preset already exists: {preset.name}")
            self._presets[key] = preset
        return preset

    def register_effects(
        self,
        name: str,
        effects: Iterable[AudioEffect],
        *,
        description: str = "",
        overwrite: bool = False,
    ) -> AudioPreset:
        return self.register(
            AudioPreset.from_effects(name, effects, description=description),
            overwrite=overwrite,
        )

    def capture_bus(
        self,
        name: str,
        bus: AudioBus,
        *,
        description: str = "",
        overwrite: bool = False,
    ) -> AudioPreset:
        return self.register(
            AudioPreset.from_bus(name, bus, description=description),
            overwrite=overwrite,
        )

    def unregister(self, name: str) -> AudioPreset:
        key = _normalize_name(name).casefold()
        with self._lock:
            try:
                return self._presets.pop(key)
            except KeyError as exc:
                raise KeyError(f"Unknown audio preset: {name}") from exc

    def has(self, name: str) -> bool:
        key = str(name).strip().casefold()
        with self._lock:
            return bool(key) and key in self._presets

    def get(self, name: str) -> AudioPreset:
        key = _normalize_name(name).casefold()
        with self._lock:
            try:
                return self._presets[key]
            except KeyError as exc:
                raise KeyError(f"Unknown audio preset: {name}") from exc

    @property
    def presets(self) -> tuple[AudioPreset, ...]:
        with self._lock:
            return tuple(sorted(self._presets.values(), key=lambda p: p.name.casefold()))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(preset.name for preset in self.presets)

    def apply(
        self,
        name: str,
        bus: AudioBus,
        *,
        replace: bool = True,
    ) -> tuple[AudioEffect, ...]:
        preset = self.get(name)
        effects = preset.instantiate_effects()
        if replace:
            bus.clear_effects()
        for effect in effects:
            bus.add_effect(effect)
        return effects

    def save(self, name: str, path: str | Path) -> Path:
        preset = self.get(name)
        return audio_preset_codec.save(preset, path)

    def load(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
        name: str | None = None,
    ) -> AudioPreset:
        preset = audio_preset_codec.load(path)
        if name is not None:
            preset = AudioPreset(
                name=name,
                description=preset.description,
                effects=preset.effects,
            )
        return self.register(preset, overwrite=overwrite)


def create_builtin_presets() -> tuple[AudioPreset, ...]:
    """Return Nexora's default game-audio DSP presets."""

    return (
        AudioPreset.from_effects(
            "Radio",
            (
                NoiseGateEffect(-42.0, 1.0, 20.0, 80.0),
                HighPassFilterEffect(260.0, q=0.8),
                LowPassFilterEffect(4_800.0, q=0.8),
                ParametricEQEffect(1_800.0, 3.0, 1.1),
                CompressorEffect(-20.0, 4.0, 4.0, 90.0, 2.0),
                DistortionEffect(drive=1.6, output_gain_db=-1.0, wet=0.2),
            ),
            description="Band-limited compressed radio/voice communication.",
        ),
        AudioPreset.from_effects(
            "Telephone",
            (
                HighPassFilterEffect(420.0, q=0.9),
                LowPassFilterEffect(3_300.0, q=0.9),
                ParametricEQEffect(1_600.0, 4.0, 1.0),
                CompressorEffect(-22.0, 5.0, 3.0, 80.0, 2.5),
            ),
            description="Narrow-band telephone sound.",
        ),
        AudioPreset.from_effects(
            "Underwater",
            (
                LowPassFilterEffect(900.0, q=0.75),
                ParametricEQEffect(180.0, 3.0, 0.8),
                ReverbEffect(0.65, 0.75, 0.72, wet=0.32),
            ),
            description="Muffled underwater ambience.",
        ),
        AudioPreset.from_effects(
            "Cave",
            (
                HighPassFilterEffect(80.0),
                DelayEffect(0.085, 0.18, wet=0.14),
                ReverbEffect(0.9, 0.28, 0.9, wet=0.48),
            ),
            description="Large reflective cave space.",
        ),
        AudioPreset.from_effects(
            "Hall",
            (
                HighPassFilterEffect(70.0),
                ReverbEffect(0.82, 0.38, 0.84, wet=0.36),
            ),
            description="Large hall reverb.",
        ),
        AudioPreset.from_effects(
            "Distorted Speaker",
            (
                HighPassFilterEffect(180.0),
                LowPassFilterEffect(6_500.0),
                DistortionEffect(drive=3.2, output_gain_db=-3.0, wet=0.7),
                CompressorEffect(-16.0, 6.0, 2.0, 70.0, -1.0),
            ),
            description="Overdriven small speaker / PA character.",
        ),
        AudioPreset.from_effects(
            "Wide Music",
            (
                StereoWidthEffect(1.35, wet=1.0),
                CompressorEffect(-10.0, 2.0, 15.0, 180.0, 0.0, wet=0.35),
            ),
            description="Gentle stereo widening and glue compression.",
        ),
    )
