from __future__ import annotations

import math

from nexora.lighting import LightSnapshot
from nexora.nodes.node import Node


class Light2D(Node):
    """Attachable radial 2D light.

    The node itself owns only editor-friendly light properties. During render
    it submits a LightSnapshot to renderer.lighting; the fullscreen lighting
    pass performs the actual illumination.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.color: tuple[float, float, float] = (1.0, 0.85, 0.60)
        self.radius = 180.0
        self.intensity = 1.0
        self.falloff = 2.0
        self.light_enabled = True
        self.light_mask = 0xFFFFFFFF

        # Optional procedural modulation. Values are deterministic so lights
        # remain stable/reproducible in tests and replays.
        self.flicker_enabled = False
        self.flicker_strength = 0.12
        self.flicker_speed = 17.0
        self.pulse_enabled = False
        self.pulse_amount = 0.15
        self.pulse_speed = 2.0

        self.debug_draw = False
        self.debug_layer = 100_000
        self._elapsed = 0.0

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @property
    def effective_intensity(self) -> float:
        value = max(0.0, float(self.intensity))

        if self.pulse_enabled and self.pulse_amount != 0.0:
            wave = 0.5 + 0.5 * math.sin(self._elapsed * self.pulse_speed * math.tau)
            value *= max(0.0, 1.0 - self.pulse_amount + wave * self.pulse_amount * 2.0)

        if self.flicker_enabled and self.flicker_strength != 0.0:
            # Blend two non-harmonic waves for a cheap deterministic flicker.
            phase = self._elapsed * self.flicker_speed
            noise = (
                math.sin(phase * 1.73)
                + math.sin(phase * 3.11 + 1.37)
            ) * 0.25 + 0.5
            value *= max(0.0, 1.0 - self.flicker_strength + noise * self.flicker_strength * 2.0)

        return value

    def set_color(self, red: float, green: float, blue: float) -> None:
        self.color = (
            self._clamp01(red),
            self._clamp01(green),
            self._clamp01(blue),
        )

    def update(self, delta_time: float) -> None:
        self._elapsed += max(float(delta_time), 0.0)

    def snapshot(self) -> LightSnapshot:
        x, y = self.world_position
        return LightSnapshot(
            x=float(x),
            y=float(y),
            radius=max(0.0, float(self.radius)),
            intensity=max(0.0, float(self.effective_intensity)),
            color=tuple(self._clamp01(v) for v in self.color),
            falloff=max(0.01, float(self.falloff)),
            mask=int(self.light_mask),
        )

    def render(self, renderer, interpolation: float) -> None:
        del interpolation
        if not self.light_enabled or not self.visible:
            return

        snapshot = self.snapshot()
        renderer.lighting.submit(snapshot)

        if self.debug_draw:
            renderer.circle(
                snapshot.x,
                snapshot.y,
                snapshot.radius * 2.0,
                color=(
                    snapshot.color[0],
                    snapshot.color[1],
                    snapshot.color[2],
                    0.08,
                ),
                layer=int(self.debug_layer),
            )
            renderer.circle(
                snapshot.x,
                snapshot.y,
                8.0,
                color=(
                    snapshot.color[0],
                    snapshot.color[1],
                    snapshot.color[2],
                    0.9,
                ),
                layer=int(self.debug_layer) + 1,
            )
