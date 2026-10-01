from __future__ import annotations

from abc import ABC, abstractmethod
from threading import RLock
from typing import Any

import numpy as np


class AudioEffect(ABC):
    """Base class for in-place bus DSP effects.

    Effects expose a thread-safe bypass/wet-dry layer. The DSP implementation
    itself still processes a fully-wet block in-place; :meth:`process_mixed`
    handles the dry/wet blend without changing effect implementations.
    """

    effect_type = "effect"

    def __init__(
        self,
        *,
        enabled: bool = True,
        wet: float = 1.0,
    ) -> None:
        self._parameter_lock = RLock()
        self._enabled = bool(enabled)
        self._wet = 1.0
        self.wet = wet

    @property
    def enabled(self) -> bool:
        with self._parameter_lock:
            return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        with self._parameter_lock:
            self._enabled = bool(value)

    @property
    def bypassed(self) -> bool:
        return not self.enabled

    @bypassed.setter
    def bypassed(self, value: bool) -> None:
        self.enabled = not bool(value)

    @property
    def wet(self) -> float:
        with self._parameter_lock:
            return self._wet

    @wet.setter
    def wet(self, value: float) -> None:
        value = float(value)
        if not 0.0 <= value <= 1.0:
            raise ValueError("Effect wet value must be between 0.0 and 1.0.")
        with self._parameter_lock:
            self._wet = value

    @abstractmethod
    def process(
        self,
        buffer: np.ndarray,
        *,
        sample_rate: int,
        channels: int,
    ) -> None:
        """Process a fully-wet audio block in-place."""

    def process_mixed(
        self,
        buffer: np.ndarray,
        scratch: np.ndarray,
        *,
        sample_rate: int,
        channels: int,
    ) -> None:
        """Process bypass and wet/dry blending with reusable scratch memory."""
        with self._parameter_lock:
            enabled = self._enabled
            wet = self._wet

        if not enabled or wet <= 0.0:
            return
        if wet >= 1.0:
            self.process(buffer, sample_rate=sample_rate, channels=channels)
            return

        np.copyto(scratch, buffer)
        self.process(scratch, sample_rate=sample_rate, channels=channels)
        np.multiply(buffer, 1.0 - wet, out=buffer)
        np.multiply(scratch, wet, out=scratch)
        np.add(buffer, scratch, out=buffer)

    def set_parameter(self, name: str, value: Any) -> None:
        """Set a public effect parameter through its normal property setter."""
        name = str(name).strip()
        if not name or name.startswith("_") or not hasattr(type(self), name):
            raise KeyError(f"Unknown effect parameter: {name}")
        setattr(self, name, value)

    def get_parameter(self, name: str) -> Any:
        name = str(name).strip()
        if not name or name.startswith("_") or not hasattr(type(self), name):
            raise KeyError(f"Unknown effect parameter: {name}")
        return getattr(self, name)

    def reset(self) -> None:
        """Reset state held across audio blocks, if any."""

    def _parameter_state(self) -> dict[str, Any]:
        return {}

    def to_state(self) -> dict[str, Any]:
        return {
            "type": self.effect_type,
            "enabled": self.enabled,
            "wet": self.wet,
            "parameters": self._parameter_state(),
        }


class GainEffect(AudioEffect):
    """Simple linear gain stage useful for testing/custom bus chains."""

    effect_type = "gain"

    def __init__(
        self,
        gain: float = 1.0,
        *,
        enabled: bool = True,
        wet: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.gain = gain

    @property
    def gain(self) -> float:
        with self._parameter_lock:
            return self._gain

    @gain.setter
    def gain(self, value: float) -> None:
        with self._parameter_lock:
            self._gain = float(value)

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        del sample_rate, channels
        gain = self.gain
        np.multiply(buffer, gain, out=buffer)

    def _parameter_state(self) -> dict[str, Any]:
        return {"gain": self.gain}


class LimiterEffect(AudioEffect):
    """Lightweight hard limiter for a bus or the master output."""

    effect_type = "limiter"

    def __init__(
        self,
        threshold: float = 1.0,
        *,
        enabled: bool = True,
        wet: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.threshold = threshold

    @property
    def threshold(self) -> float:
        with self._parameter_lock:
            return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("Limiter threshold must be greater than 0.")
        with self._parameter_lock:
            self._threshold = value

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        del sample_rate, channels
        threshold = self.threshold
        np.clip(buffer, -threshold, threshold, out=buffer)

    def _parameter_state(self) -> dict[str, Any]:
        return {"threshold": self.threshold}


def audio_effect_from_state(state: dict[str, Any]) -> AudioEffect:
    """Recreate a built-in Nexora effect from snapshot state."""
    effect_type = str(state.get("type", "")).casefold()
    enabled = bool(state.get("enabled", True))
    wet = float(state.get("wet", 1.0))
    parameters = dict(state.get("parameters") or {})

    if effect_type == GainEffect.effect_type:
        return GainEffect(
            float(parameters.get("gain", 1.0)), enabled=enabled, wet=wet
        )
    if effect_type == LimiterEffect.effect_type:
        return LimiterEffect(
            float(parameters.get("threshold", 1.0)), enabled=enabled, wet=wet
        )
    if effect_type == LowPassFilterEffect.effect_type:
        return LowPassFilterEffect(float(parameters.get("cutoff_hz", 12000.0)), float(parameters.get("q", 0.70710678)), enabled=enabled, wet=wet)
    if effect_type == HighPassFilterEffect.effect_type:
        return HighPassFilterEffect(float(parameters.get("cutoff_hz", 80.0)), float(parameters.get("q", 0.70710678)), enabled=enabled, wet=wet)
    if effect_type == ParametricEQEffect.effect_type:
        return ParametricEQEffect(float(parameters.get("frequency_hz", 1000.0)), float(parameters.get("gain_db", 0.0)), float(parameters.get("q", 1.0)), enabled=enabled, wet=wet)
    if effect_type == CompressorEffect.effect_type:
        return CompressorEffect(float(parameters.get("threshold_db", -12.0)), float(parameters.get("ratio", 4.0)), float(parameters.get("attack_ms", 10.0)), float(parameters.get("release_ms", 100.0)), float(parameters.get("makeup_gain_db", 0.0)), enabled=enabled, wet=wet)
    if effect_type == DelayEffect.effect_type:
        return DelayEffect(float(parameters.get("delay_seconds", 0.25)), float(parameters.get("feedback", 0.35)), enabled=enabled, wet=wet)
    if effect_type == ReverbEffect.effect_type:
        return ReverbEffect(float(parameters.get("room_size", 0.5)), float(parameters.get("damping", 0.35)), float(parameters.get("decay", 0.65)), enabled=enabled, wet=wet)
    if effect_type == DistortionEffect.effect_type:
        return DistortionEffect(
            drive=float(parameters.get("drive", 2.0)),
            output_gain_db=float(parameters.get("output_gain_db", 0.0)),
            mode=str(parameters.get("mode", "soft")),
            enabled=enabled,
            wet=wet,
        )
    if effect_type == NoiseGateEffect.effect_type:
        return NoiseGateEffect(
            threshold_db=float(parameters.get("threshold_db", -40.0)),
            attack_ms=float(parameters.get("attack_ms", 2.0)),
            hold_ms=float(parameters.get("hold_ms", 25.0)),
            release_ms=float(parameters.get("release_ms", 80.0)),
            enabled=enabled,
            wet=wet,
        )
    if effect_type == StereoWidthEffect.effect_type:
        return StereoWidthEffect(
            width=float(parameters.get("width", 1.0)),
            enabled=enabled,
            wet=wet,
        )
    raise ValueError(f"Unknown built-in audio effect type: {effect_type!r}")


class _BiquadEffect(AudioEffect):
    """Shared stateful Direct Form I biquad implementation."""

    def __init__(self, *, enabled: bool = True, wet: float = 1.0) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self._state_channels = 0
        self._x1 = np.zeros(0, dtype=np.float32)
        self._x2 = np.zeros(0, dtype=np.float32)
        self._y1 = np.zeros(0, dtype=np.float32)
        self._y2 = np.zeros(0, dtype=np.float32)

    def _ensure_state(self, channels: int) -> None:
        channels = max(1, int(channels))
        if channels == self._state_channels:
            return
        self._state_channels = channels
        self._x1 = np.zeros(channels, dtype=np.float32)
        self._x2 = np.zeros(channels, dtype=np.float32)
        self._y1 = np.zeros(channels, dtype=np.float32)
        self._y2 = np.zeros(channels, dtype=np.float32)

    def reset(self) -> None:
        self._x1.fill(0.0)
        self._x2.fill(0.0)
        self._y1.fill(0.0)
        self._y2.fill(0.0)

    def _coefficients(self, sample_rate: int) -> tuple[float, float, float, float, float]:
        raise NotImplementedError

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        if buffer.size == 0:
            return
        actual_channels = int(buffer.shape[1]) if buffer.ndim > 1 else 1
        self._ensure_state(actual_channels)
        b0, b1, b2, a1, a2 = self._coefficients(sample_rate)

        x1 = self._x1
        x2 = self._x2
        y1 = self._y1
        y2 = self._y2
        frames = buffer if buffer.ndim > 1 else buffer.reshape(-1, 1)

        for i in range(frames.shape[0]):
            x = frames[i].copy()
            y = (b0 * x) + (b1 * x1) + (b2 * x2) - (a1 * y1) - (a2 * y2)
            frames[i] = y
            x2[:] = x1
            x1[:] = x
            y2[:] = y1
            y1[:] = y


class LowPassFilterEffect(_BiquadEffect):
    """Resonant low-pass filter implemented as a stateful biquad."""

    effect_type = "lowpass"

    def __init__(self, cutoff_hz: float = 12_000.0, q: float = 0.70710678, *, enabled: bool = True, wet: float = 1.0) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.cutoff_hz = cutoff_hz
        self.q = q

    @property
    def cutoff_hz(self) -> float:
        with self._parameter_lock:
            return self._cutoff_hz

    @cutoff_hz.setter
    def cutoff_hz(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("Low-pass cutoff_hz must be greater than 0.")
        with self._parameter_lock:
            self._cutoff_hz = value

    @property
    def q(self) -> float:
        with self._parameter_lock:
            return self._q

    @q.setter
    def q(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("Low-pass q must be greater than 0.")
        with self._parameter_lock:
            self._q = value

    def _coefficients(self, sample_rate: int):
        cutoff = min(self.cutoff_hz, max(1.0, sample_rate * 0.499))
        q = self.q
        w0 = 2.0 * np.pi * cutoff / float(sample_rate)
        c = float(np.cos(w0))
        s = float(np.sin(w0))
        alpha = s / (2.0 * q)
        b0 = (1.0 - c) * 0.5
        b1 = 1.0 - c
        b2 = b0
        a0 = 1.0 + alpha
        a1 = -2.0 * c
        a2 = 1.0 - alpha
        return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0

    def _parameter_state(self) -> dict[str, Any]:
        return {"cutoff_hz": self.cutoff_hz, "q": self.q}


class HighPassFilterEffect(_BiquadEffect):
    """Resonant high-pass filter implemented as a stateful biquad."""

    effect_type = "highpass"

    def __init__(self, cutoff_hz: float = 80.0, q: float = 0.70710678, *, enabled: bool = True, wet: float = 1.0) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.cutoff_hz = cutoff_hz
        self.q = q

    @property
    def cutoff_hz(self) -> float:
        with self._parameter_lock:
            return self._cutoff_hz

    @cutoff_hz.setter
    def cutoff_hz(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("High-pass cutoff_hz must be greater than 0.")
        with self._parameter_lock:
            self._cutoff_hz = value

    @property
    def q(self) -> float:
        with self._parameter_lock:
            return self._q

    @q.setter
    def q(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("High-pass q must be greater than 0.")
        with self._parameter_lock:
            self._q = value

    def _coefficients(self, sample_rate: int):
        cutoff = min(self.cutoff_hz, max(1.0, sample_rate * 0.499))
        q = self.q
        w0 = 2.0 * np.pi * cutoff / float(sample_rate)
        c = float(np.cos(w0))
        s = float(np.sin(w0))
        alpha = s / (2.0 * q)
        b0 = (1.0 + c) * 0.5
        b1 = -(1.0 + c)
        b2 = b0
        a0 = 1.0 + alpha
        a1 = -2.0 * c
        a2 = 1.0 - alpha
        return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0

    def _parameter_state(self) -> dict[str, Any]:
        return {"cutoff_hz": self.cutoff_hz, "q": self.q}


class ParametricEQEffect(_BiquadEffect):
    """Single peaking parametric EQ band."""

    effect_type = "parametric_eq"

    def __init__(self, frequency_hz: float = 1_000.0, gain_db: float = 0.0, q: float = 1.0, *, enabled: bool = True, wet: float = 1.0) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.frequency_hz = frequency_hz
        self.gain_db = gain_db
        self.q = q

    @property
    def frequency_hz(self) -> float:
        with self._parameter_lock:
            return self._frequency_hz

    @frequency_hz.setter
    def frequency_hz(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("EQ frequency_hz must be greater than 0.")
        with self._parameter_lock:
            self._frequency_hz = value

    @property
    def gain_db(self) -> float:
        with self._parameter_lock:
            return self._gain_db

    @gain_db.setter
    def gain_db(self, value: float) -> None:
        with self._parameter_lock:
            self._gain_db = float(value)

    @property
    def q(self) -> float:
        with self._parameter_lock:
            return self._q

    @q.setter
    def q(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("EQ q must be greater than 0.")
        with self._parameter_lock:
            self._q = value

    def _coefficients(self, sample_rate: int):
        frequency = min(self.frequency_hz, max(1.0, sample_rate * 0.499))
        q = self.q
        gain_db = self.gain_db
        a = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * frequency / float(sample_rate)
        c = float(np.cos(w0))
        s = float(np.sin(w0))
        alpha = s / (2.0 * q)
        b0 = 1.0 + alpha * a
        b1 = -2.0 * c
        b2 = 1.0 - alpha * a
        a0 = 1.0 + alpha / a
        a1 = -2.0 * c
        a2 = 1.0 - alpha / a
        return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0

    def _parameter_state(self) -> dict[str, Any]:
        return {"frequency_hz": self.frequency_hz, "gain_db": self.gain_db, "q": self.q}


class CompressorEffect(AudioEffect):
    """Stereo-linked feed-forward compressor with attack/release smoothing."""

    effect_type = "compressor"

    def __init__(self, threshold_db: float = -12.0, ratio: float = 4.0, attack_ms: float = 10.0, release_ms: float = 100.0, makeup_gain_db: float = 0.0, *, enabled: bool = True, wet: float = 1.0) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.threshold_db = threshold_db
        self.ratio = ratio
        self.attack_ms = attack_ms
        self.release_ms = release_ms
        self.makeup_gain_db = makeup_gain_db
        self._gain_reduction_db = 0.0

    @property
    def threshold_db(self):
        with self._parameter_lock: return self._threshold_db
    @threshold_db.setter
    def threshold_db(self, value):
        with self._parameter_lock: self._threshold_db = float(value)

    @property
    def ratio(self):
        with self._parameter_lock: return self._ratio
    @ratio.setter
    def ratio(self, value):
        value = float(value)
        if value < 1.0: raise ValueError("Compressor ratio must be >= 1.0.")
        with self._parameter_lock: self._ratio = value

    @property
    def attack_ms(self):
        with self._parameter_lock: return self._attack_ms
    @attack_ms.setter
    def attack_ms(self, value):
        value = float(value)
        if value < 0.0: raise ValueError("Compressor attack_ms must be >= 0.")
        with self._parameter_lock: self._attack_ms = value

    @property
    def release_ms(self):
        with self._parameter_lock: return self._release_ms
    @release_ms.setter
    def release_ms(self, value):
        value = float(value)
        if value < 0.0: raise ValueError("Compressor release_ms must be >= 0.")
        with self._parameter_lock: self._release_ms = value

    @property
    def makeup_gain_db(self):
        with self._parameter_lock: return self._makeup_gain_db
    @makeup_gain_db.setter
    def makeup_gain_db(self, value):
        with self._parameter_lock: self._makeup_gain_db = float(value)

    @property
    def gain_reduction_db(self) -> float:
        return float(self._gain_reduction_db)

    def reset(self) -> None:
        self._gain_reduction_db = 0.0

    @staticmethod
    def _time_coeff(ms: float, sample_rate: int) -> float:
        if ms <= 0.0: return 0.0
        return float(np.exp(-1.0 / (0.001 * ms * sample_rate)))

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        del channels
        if buffer.size == 0: return
        with self._parameter_lock:
            threshold = self._threshold_db
            ratio = self._ratio
            attack = self._attack_ms
            release = self._release_ms
            makeup = self._makeup_gain_db
        frames = buffer if buffer.ndim > 1 else buffer.reshape(-1, 1)
        attack_c = self._time_coeff(attack, sample_rate)
        release_c = self._time_coeff(release, sample_rate)
        gr = float(self._gain_reduction_db)
        makeup_lin = 10.0 ** (makeup / 20.0)
        for i in range(frames.shape[0]):
            peak = float(np.max(np.abs(frames[i])))
            level_db = 20.0 * np.log10(max(peak, 1e-12))
            target_gr = 0.0
            if level_db > threshold:
                compressed_db = threshold + (level_db - threshold) / ratio
                target_gr = compressed_db - level_db
            coeff = attack_c if target_gr < gr else release_c
            gr = coeff * gr + (1.0 - coeff) * target_gr
            gain = (10.0 ** (gr / 20.0)) * makeup_lin
            frames[i] *= gain
        self._gain_reduction_db = gr

    def _parameter_state(self) -> dict[str, Any]:
        return {"threshold_db": self.threshold_db, "ratio": self.ratio, "attack_ms": self.attack_ms, "release_ms": self.release_ms, "makeup_gain_db": self.makeup_gain_db}


class DelayEffect(AudioEffect):
    """Feedback delay. The effect output is fully wet; use ``wet`` for dry/wet."""

    effect_type = "delay"

    def __init__(self, delay_seconds: float = 0.25, feedback: float = 0.35, *, enabled: bool = True, wet: float = 0.25) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.delay_seconds = delay_seconds
        self.feedback = feedback
        self._delay_buffer = np.zeros((0, 0), dtype=np.float32)
        self._delay_index = 0
        self._delay_signature = None

    @property
    def delay_seconds(self):
        with self._parameter_lock: return self._delay_seconds
    @delay_seconds.setter
    def delay_seconds(self, value):
        value = float(value)
        if value <= 0.0: raise ValueError("Delay delay_seconds must be > 0.")
        with self._parameter_lock: self._delay_seconds = value

    @property
    def feedback(self):
        with self._parameter_lock: return self._feedback
    @feedback.setter
    def feedback(self, value):
        value = float(value)
        if not -0.99 <= value <= 0.99: raise ValueError("Delay feedback must be between -0.99 and 0.99.")
        with self._parameter_lock: self._feedback = value

    def _ensure_delay(self, sample_rate: int, channels: int, delay_seconds: float) -> None:
        length = max(1, int(round(delay_seconds * sample_rate)))
        signature = (length, channels)
        if signature == self._delay_signature: return
        self._delay_buffer = np.zeros((length, channels), dtype=np.float32)
        self._delay_index = 0
        self._delay_signature = signature

    def reset(self) -> None:
        self._delay_buffer.fill(0.0)
        self._delay_index = 0

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        if buffer.size == 0: return
        frames = buffer if buffer.ndim > 1 else buffer.reshape(-1, 1)
        actual_channels = frames.shape[1]
        with self._parameter_lock:
            delay_seconds = self._delay_seconds
            feedback = self._feedback
        self._ensure_delay(sample_rate, actual_channels, delay_seconds)
        line = self._delay_buffer
        idx = self._delay_index
        n = line.shape[0]
        for i in range(frames.shape[0]):
            dry = frames[i].copy()
            delayed = line[idx].copy()
            frames[i] = delayed
            line[idx] = dry + delayed * feedback
            idx += 1
            if idx >= n: idx = 0
        self._delay_index = idx

    def _parameter_state(self) -> dict[str, Any]:
        return {"delay_seconds": self.delay_seconds, "feedback": self.feedback}


class ReverbEffect(AudioEffect):
    """Compact Schroeder-style reverb using parallel damped feedback combs."""

    effect_type = "reverb"
    _BASE_DELAYS = (0.0297, 0.0371, 0.0411, 0.0437)

    def __init__(self, room_size: float = 0.5, damping: float = 0.35, decay: float = 0.65, *, enabled: bool = True, wet: float = 0.2) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.room_size = room_size
        self.damping = damping
        self.decay = decay
        self._lines: list[np.ndarray] = []
        self._indices: list[int] = []
        self._damped: list[np.ndarray] = []
        self._wet_sum = np.zeros(0, dtype=np.float32)
        self._signature = None

    @property
    def room_size(self):
        with self._parameter_lock: return self._room_size
    @room_size.setter
    def room_size(self, value):
        value = float(value)
        if not 0.0 <= value <= 1.0: raise ValueError("Reverb room_size must be between 0 and 1.")
        with self._parameter_lock: self._room_size = value

    @property
    def damping(self):
        with self._parameter_lock: return self._damping
    @damping.setter
    def damping(self, value):
        value = float(value)
        if not 0.0 <= value <= 1.0: raise ValueError("Reverb damping must be between 0 and 1.")
        with self._parameter_lock: self._damping = value

    @property
    def decay(self):
        with self._parameter_lock: return self._decay
    @decay.setter
    def decay(self, value):
        value = float(value)
        if not 0.0 <= value < 1.0: raise ValueError("Reverb decay must be >= 0 and < 1.")
        with self._parameter_lock: self._decay = value

    def _ensure_lines(self, sample_rate: int, channels: int, room_size: float) -> None:
        scale = 0.65 + 0.7 * room_size
        lengths = tuple(max(1, int(round(d * scale * sample_rate))) for d in self._BASE_DELAYS)
        signature = (lengths, channels)
        if signature == self._signature: return
        self._lines = [np.zeros((n, channels), dtype=np.float32) for n in lengths]
        self._indices = [0 for _ in lengths]
        self._damped = [np.zeros(channels, dtype=np.float32) for _ in lengths]
        self._wet_sum = np.zeros(channels, dtype=np.float32)
        self._signature = signature

    def reset(self) -> None:
        for line in self._lines: line.fill(0.0)
        for damped in self._damped: damped.fill(0.0)
        for i in range(len(self._indices)): self._indices[i] = 0

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        if buffer.size == 0: return
        frames = buffer if buffer.ndim > 1 else buffer.reshape(-1, 1)
        actual_channels = frames.shape[1]
        with self._parameter_lock:
            room = self._room_size
            damping = self._damping
            decay = self._decay
        self._ensure_lines(sample_rate, actual_channels, room)
        wet_sum = self._wet_sum
        for frame_index in range(frames.shape[0]):
            dry = frames[frame_index].copy()
            wet_sum.fill(0.0)
            for line_index, line in enumerate(self._lines):
                idx = self._indices[line_index]
                delayed = line[idx]
                damped = self._damped[line_index]
                damped *= damping
                damped += delayed * (1.0 - damping)
                wet_sum += delayed
                line[idx] = dry + damped * decay
                idx += 1
                if idx >= line.shape[0]: idx = 0
                self._indices[line_index] = idx
            frames[frame_index] = wet_sum * (1.0 / len(self._lines))

    def _parameter_state(self) -> dict[str, Any]:
        return {"room_size": self.room_size, "damping": self.damping, "decay": self.decay}

class DistortionEffect(AudioEffect):
    """Non-linear distortion/saturation with soft or hard clipping.

    ``drive`` controls how strongly the signal is pushed into the transfer
    function. ``output_gain_db`` is applied after distortion. The inherited
    ``wet`` parameter provides parallel saturation without another buffer API.
    """

    effect_type = "distortion"
    _VALID_MODES = {"soft", "hard"}

    def __init__(
        self,
        drive: float = 2.0,
        output_gain_db: float = 0.0,
        mode: str = "soft",
        *,
        enabled: bool = True,
        wet: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.drive = drive
        self.output_gain_db = output_gain_db
        self.mode = mode

    @property
    def drive(self) -> float:
        with self._parameter_lock:
            return self._drive

    @drive.setter
    def drive(self, value: float) -> None:
        value = float(value)
        if value <= 0.0:
            raise ValueError("Distortion drive must be greater than 0.")
        with self._parameter_lock:
            self._drive = value

    @property
    def output_gain_db(self) -> float:
        with self._parameter_lock:
            return self._output_gain_db

    @output_gain_db.setter
    def output_gain_db(self, value: float) -> None:
        with self._parameter_lock:
            self._output_gain_db = float(value)

    @property
    def mode(self) -> str:
        with self._parameter_lock:
            return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        value = str(value).strip().casefold()
        if value not in self._VALID_MODES:
            raise ValueError("Distortion mode must be 'soft' or 'hard'.")
        with self._parameter_lock:
            self._mode = value

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        del sample_rate, channels
        if buffer.size == 0:
            return
        with self._parameter_lock:
            drive = self._drive
            output_gain = 10.0 ** (self._output_gain_db / 20.0)
            mode = self._mode

        np.multiply(buffer, drive, out=buffer)
        if mode == "soft":
            # tanh is smooth around zero and approaches +/-1 asymptotically.
            np.tanh(buffer, out=buffer)
        else:
            np.clip(buffer, -1.0, 1.0, out=buffer)
        if output_gain != 1.0:
            np.multiply(buffer, output_gain, out=buffer)

    def _parameter_state(self) -> dict[str, Any]:
        return {
            "drive": self.drive,
            "output_gain_db": self.output_gain_db,
            "mode": self.mode,
        }


class NoiseGateEffect(AudioEffect):
    """Stereo-linked noise gate with attack, hold and release smoothing."""

    effect_type = "noise_gate"

    def __init__(
        self,
        threshold_db: float = -40.0,
        attack_ms: float = 2.0,
        hold_ms: float = 25.0,
        release_ms: float = 80.0,
        *,
        enabled: bool = True,
        wet: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.threshold_db = threshold_db
        self.attack_ms = attack_ms
        self.hold_ms = hold_ms
        self.release_ms = release_ms
        self._gain = 0.0
        self._hold_remaining = 0

    @property
    def threshold_db(self) -> float:
        with self._parameter_lock:
            return self._threshold_db

    @threshold_db.setter
    def threshold_db(self, value: float) -> None:
        with self._parameter_lock:
            self._threshold_db = float(value)

    @property
    def attack_ms(self) -> float:
        with self._parameter_lock:
            return self._attack_ms

    @attack_ms.setter
    def attack_ms(self, value: float) -> None:
        value = float(value)
        if value < 0.0:
            raise ValueError("Noise gate attack_ms must be >= 0.")
        with self._parameter_lock:
            self._attack_ms = value

    @property
    def hold_ms(self) -> float:
        with self._parameter_lock:
            return self._hold_ms

    @hold_ms.setter
    def hold_ms(self, value: float) -> None:
        value = float(value)
        if value < 0.0:
            raise ValueError("Noise gate hold_ms must be >= 0.")
        with self._parameter_lock:
            self._hold_ms = value

    @property
    def release_ms(self) -> float:
        with self._parameter_lock:
            return self._release_ms

    @release_ms.setter
    def release_ms(self, value: float) -> None:
        value = float(value)
        if value < 0.0:
            raise ValueError("Noise gate release_ms must be >= 0.")
        with self._parameter_lock:
            self._release_ms = value

    @property
    def gain(self) -> float:
        """Current smoothed gate gain, useful for meters/debugging."""
        return float(self._gain)

    @staticmethod
    def _time_coeff(ms: float, sample_rate: int) -> float:
        if ms <= 0.0:
            return 0.0
        return float(np.exp(-1.0 / (0.001 * ms * sample_rate)))

    def reset(self) -> None:
        self._gain = 0.0
        self._hold_remaining = 0

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        del channels
        if buffer.size == 0:
            return
        frames = buffer if buffer.ndim > 1 else buffer.reshape(-1, 1)
        with self._parameter_lock:
            threshold_linear = 10.0 ** (self._threshold_db / 20.0)
            attack_ms = self._attack_ms
            hold_samples = max(0, int(round(self._hold_ms * 0.001 * sample_rate)))
            release_ms = self._release_ms

        attack_c = self._time_coeff(attack_ms, sample_rate)
        release_c = self._time_coeff(release_ms, sample_rate)
        gain = float(self._gain)
        hold_remaining = int(self._hold_remaining)

        for i in range(frames.shape[0]):
            peak = float(np.max(np.abs(frames[i])))
            if peak >= threshold_linear:
                target = 1.0
                hold_remaining = hold_samples
            elif hold_remaining > 0:
                target = 1.0
                hold_remaining -= 1
            else:
                target = 0.0

            coeff = attack_c if target > gain else release_c
            gain = coeff * gain + (1.0 - coeff) * target
            frames[i] *= gain

        self._gain = gain
        self._hold_remaining = hold_remaining

    def _parameter_state(self) -> dict[str, Any]:
        return {
            "threshold_db": self.threshold_db,
            "attack_ms": self.attack_ms,
            "hold_ms": self.hold_ms,
            "release_ms": self.release_ms,
        }


class StereoWidthEffect(AudioEffect):
    """Mid/side stereo-width processor.

    ``width=0`` collapses to mono, ``1`` is neutral and ``2`` doubles the side
    component. Mono buffers are intentionally left unchanged.
    """

    effect_type = "stereo_width"

    def __init__(
        self,
        width: float = 1.0,
        *,
        enabled: bool = True,
        wet: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, wet=wet)
        self.width = width

    @property
    def width(self) -> float:
        with self._parameter_lock:
            return self._width

    @width.setter
    def width(self, value: float) -> None:
        value = float(value)
        if not 0.0 <= value <= 2.0:
            raise ValueError("Stereo width must be between 0.0 and 2.0.")
        with self._parameter_lock:
            self._width = value

    def process(self, buffer: np.ndarray, *, sample_rate: int, channels: int) -> None:
        del sample_rate, channels
        if buffer.size == 0 or buffer.ndim < 2 or buffer.shape[1] < 2:
            return
        width = self.width
        if width == 1.0:
            return

        left = buffer[:, 0]
        right = buffer[:, 1]
        # Copy one temporary side vector so in-place writes cannot corrupt the
        # right-channel input. This allocation is one vector per processed
        # block; bus-level wet/dry scratch remains reusable in the mixer.
        mid = (left + right) * 0.5
        side = (left - right) * (0.5 * width)
        np.add(mid, side, out=left)
        np.subtract(mid, side, out=right)

    def _parameter_state(self) -> dict[str, Any]:
        return {"width": self.width}

