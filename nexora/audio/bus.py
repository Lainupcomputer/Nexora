from __future__ import annotations

import math
from threading import RLock
from uuid import uuid4

import numpy as np

from .effects import AudioEffect


def _linear_to_dbfs(value: float) -> float:
    value = abs(float(value))
    if value <= 0.0:
        return float("-inf")
    return 20.0 * math.log10(value)


class AudioBus:
    """A named node in Nexora's hierarchical audio bus graph."""

    def __init__(
        self,
        name: str,
        volume: float = 1.0,
        muted: bool = False,
        *,
        parent: "AudioBus | None" = None,
        pan: float = 0.0,
        solo: bool = False,
        bus_id: str | None = None,
    ) -> None:
        name = str(name).strip()
        if not name:
            raise ValueError("Audio bus name must not be empty.")

        self._id = str(bus_id or uuid4().hex)
        self.name = name
        self._volume = 1.0
        self._muted = bool(muted)
        self._parent: AudioBus | None = None
        self._pan = 0.0
        self._solo = bool(solo)
        self._effects_bypassed = False
        self._effects: list[AudioEffect] = []
        self._effects_lock = RLock()
        self._effect_scratch = np.empty((0, 2), dtype=np.float32)
        self._meter_lock = RLock()
        self._peak = (0.0, 0.0)
        self._rms = (0.0, 0.0)
        self._peak_hold = (0.0, 0.0)
        self._clipped = False
        self.volume = volume
        self.pan = pan
        self.parent = parent

    @property
    def id(self) -> str:
        return self._id

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        value = float(value)
        if value < 0.0:
            raise ValueError("Audio bus volume must not be negative.")
        self._volume = value

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        self._muted = bool(value)

    @property
    def pan(self) -> float:
        return self._pan

    @pan.setter
    def pan(self, value: float) -> None:
        value = float(value)
        if not -1.0 <= value <= 1.0:
            raise ValueError("Audio bus pan must be between -1.0 and 1.0.")
        self._pan = value

    @property
    def solo(self) -> bool:
        return self._solo

    @solo.setter
    def solo(self, value: bool) -> None:
        self._solo = bool(value)

    @property
    def effects_bypassed(self) -> bool:
        return self._effects_bypassed

    @effects_bypassed.setter
    def effects_bypassed(self, value: bool) -> None:
        self._effects_bypassed = bool(value)

    @property
    def peak(self) -> tuple[float, float]:
        with self._meter_lock:
            return self._peak

    @property
    def rms(self) -> tuple[float, float]:
        with self._meter_lock:
            return self._rms

    @property
    def peak_hold(self) -> tuple[float, float]:
        with self._meter_lock:
            return self._peak_hold

    @property
    def clipped(self) -> bool:
        with self._meter_lock:
            return self._clipped

    @property
    def peak_dbfs(self) -> tuple[float, float]:
        left, right = self.peak
        return _linear_to_dbfs(left), _linear_to_dbfs(right)

    @property
    def rms_dbfs(self) -> tuple[float, float]:
        left, right = self.rms
        return _linear_to_dbfs(left), _linear_to_dbfs(right)

    @property
    def peak_hold_dbfs(self) -> tuple[float, float]:
        left, right = self.peak_hold
        return _linear_to_dbfs(left), _linear_to_dbfs(right)

    def update_meter(self, buffer: np.ndarray) -> None:
        if buffer.ndim != 2 or buffer.shape[0] == 0 or buffer.shape[1] < 2:
            self.reset_meter(clear_hold=False)
            return

        left = buffer[:, 0]
        right = buffer[:, 1]
        left_peak = max(abs(float(np.min(left))), abs(float(np.max(left))))
        right_peak = max(abs(float(np.min(right))), abs(float(np.max(right))))
        frames = float(buffer.shape[0])
        left_rms = float(np.sqrt(np.dot(left, left) / frames))
        right_rms = float(np.sqrt(np.dot(right, right) / frames))

        with self._meter_lock:
            self._peak = (left_peak, right_peak)
            self._rms = (left_rms, right_rms)
            self._peak_hold = (
                max(self._peak_hold[0], left_peak),
                max(self._peak_hold[1], right_peak),
            )
            self._clipped = self._clipped or left_peak >= 1.0 or right_peak >= 1.0

    def reset_meter(self, *, clear_hold: bool = True) -> None:
        with self._meter_lock:
            self._peak = (0.0, 0.0)
            self._rms = (0.0, 0.0)
            if clear_hold:
                self._peak_hold = (0.0, 0.0)
                self._clipped = False

    def clear_peak_hold(self) -> None:
        with self._meter_lock:
            self._peak_hold = (0.0, 0.0)
            self._clipped = False

    @property
    def parent(self) -> "AudioBus | None":
        return self._parent

    @parent.setter
    def parent(self, value: "AudioBus | None") -> None:
        if value is self:
            raise ValueError("An audio bus cannot be its own parent.")
        current = value
        while current is not None:
            if current is self:
                raise ValueError("Audio bus hierarchy cannot contain cycles.")
            current = current.parent
        self._parent = value

    @property
    def effective_volume(self) -> float:
        if self._muted:
            return 0.0
        volume = self._volume
        current = self._parent
        while current is not None:
            if current.muted:
                return 0.0
            volume *= current.volume
            current = current.parent
        return volume

    @property
    def effects(self) -> tuple[AudioEffect, ...]:
        with self._effects_lock:
            return tuple(self._effects)

    def add_effect(self, effect: AudioEffect, *, index: int | None = None) -> AudioEffect:
        if not isinstance(effect, AudioEffect):
            raise TypeError("effect must inherit from AudioEffect.")
        with self._effects_lock:
            if effect in self._effects:
                raise ValueError("Audio effect is already attached to this bus.")
            if index is None:
                self._effects.append(effect)
            else:
                self._effects.insert(int(index), effect)
        return effect

    def remove_effect(self, effect: AudioEffect) -> None:
        with self._effects_lock:
            self._effects.remove(effect)
            effect.reset()

    def clear_effects(self) -> None:
        with self._effects_lock:
            for effect in self._effects:
                effect.reset()
            self._effects.clear()

    def reset_effects(self) -> None:
        with self._effects_lock:
            for effect in self._effects:
                effect.reset()

    def process_effects(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        if self._effects_bypassed:
            return
        with self._effects_lock:
            if not self._effects:
                return
            if self._effect_scratch.shape[0] < buffer.shape[0] or self._effect_scratch.shape[1] != channels:
                self._effect_scratch = np.empty((buffer.shape[0], channels), dtype=np.float32)
            scratch = self._effect_scratch[: buffer.shape[0], :channels]
            for effect in self._effects:
                effect.process_mixed(
                    buffer,
                    scratch,
                    sample_rate=sample_rate,
                    channels=channels,
                )

    def mute(self) -> None:
        self._muted = True

    def unmute(self) -> None:
        self._muted = False

    def toggle_mute(self) -> None:
        self._muted = not self._muted

    def __repr__(self) -> str:
        parent = self.parent.name if self.parent is not None else None
        return (
            f"AudioBus(id={self.id!r}, name={self.name!r}, volume={self.volume!r}, "
            f"muted={self.muted!r}, pan={self.pan!r}, solo={self.solo!r}, "
            f"parent={parent!r}, effects={len(self._effects)})"
        )
