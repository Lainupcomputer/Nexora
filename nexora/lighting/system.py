from __future__ import annotations

from dataclasses import dataclass
import math

from .light import LightSnapshot
from .occluder import OccluderSnapshot


@dataclass(slots=True)
class ScreenShadowSegment:
    ax: float
    ay: float
    bx: float
    by: float


@dataclass(slots=True)
class ScreenLight:
    x: float
    y: float
    radius: float
    intensity: float
    color: tuple[float, float, float]
    falloff: float

    shadow_start: int = 0
    shadow_count: int = 0
    shadow_strength: float = 0.0
    shadow_softness: float = 0.0
    shadow_color: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(slots=True)
class _ScreenOccluderSegment:
    ax: float
    ay: float
    bx: float
    by: float
    mask: int


class LightingSystem:
    """Per-renderer 2D lighting and shadow collector.

    Light2D and LightOccluder2D submit world-space snapshots during scene
    rendering. At the end of the frame this service converts them to screen
    space and forwards a compact representation to the existing fullscreen
    post-process pass.
    """

    MAX_LIGHTS = 32
    MAX_SHADOW_SEGMENTS = 256
    MAX_SEGMENTS_PER_LIGHT = 16

    def __init__(
        self,
        *,
        max_lights: int = MAX_LIGHTS,
        max_shadow_segments: int = MAX_SHADOW_SEGMENTS,
    ) -> None:
        self.enabled = False
        self.shadows_enabled = True

        self.ambient_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
        self.ambient_intensity = 1.0
        self.visible_mask = 0xFFFFFFFF

        self.max_lights = max(1, min(int(max_lights), self.MAX_LIGHTS))
        self.max_shadow_segments = max(
            1,
            min(int(max_shadow_segments), self.MAX_SHADOW_SEGMENTS),
        )

        self._submitted: list[LightSnapshot] = []
        self._occluders: list[OccluderSnapshot] = []

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @property
    def light_count(self) -> int:
        return len(self._submitted)

    @property
    def occluder_count(self) -> int:
        return len(self._occluders)

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def enable_shadows(self) -> None:
        self.shadows_enabled = True

    def disable_shadows(self) -> None:
        self.shadows_enabled = False

    def set_ambient(
        self,
        color: tuple[float, float, float],
        intensity: float = 1.0,
    ) -> None:
        if len(color) != 3:
            raise ValueError("Ambient color must contain exactly three values")
        self.ambient_color = tuple(self._clamp01(v) for v in color)
        self.ambient_intensity = max(0.0, float(intensity))
        self.enabled = True

    def begin_frame(self) -> None:
        self._submitted.clear()
        self._occluders.clear()

    def submit(self, light: LightSnapshot) -> bool:
        if light.mask & self.visible_mask == 0:
            return False
        if len(self._submitted) >= self.max_lights:
            return False
        self._submitted.append(light)
        return True

    def submit_occluder(self, occluder: OccluderSnapshot) -> bool:
        if not occluder.segments():
            return False
        self._occluders.append(occluder)
        return True

    @staticmethod
    def _distance_to_segment(
        px: float,
        py: float,
        ax: float,
        ay: float,
        bx: float,
        by: float,
    ) -> float:
        abx = bx - ax
        aby = by - ay
        length_sq = abx * abx + aby * aby
        if length_sq <= 1e-12:
            return math.hypot(px - ax, py - ay)
        t = ((px - ax) * abx + (py - ay) * aby) / length_sq
        t = max(0.0, min(1.0, t))
        cx = ax + abx * t
        cy = ay + aby * t
        return math.hypot(px - cx, py - cy)

    def _screen_occluders(
        self,
        camera,
        width: int,
        height: int,
    ) -> tuple[_ScreenOccluderSegment, ...]:
        result: list[_ScreenOccluderSegment] = []
        for occluder in self._occluders:
            for (ax, ay), (bx, by) in occluder.segments():
                sax, say = camera.world_to_screen(ax, ay, width, height)
                sbx, sby = camera.world_to_screen(bx, by, width, height)
                result.append(
                    _ScreenOccluderSegment(
                        float(sax),
                        float(say),
                        float(sbx),
                        float(sby),
                        int(occluder.mask),
                    )
                )
        return tuple(result)

    def build_screen_frame(
        self,
        camera,
        width: int,
        height: int,
    ) -> tuple[tuple[ScreenLight, ...], tuple[ScreenShadowSegment, ...]]:
        if width <= 0 or height <= 0:
            return (), ()

        zoom = max(float(getattr(camera, "zoom", 1.0)), 0.0001)
        source_segments = self._screen_occluders(camera, width, height)
        lights: list[ScreenLight] = []
        shadow_segments: list[ScreenShadowSegment] = []

        for light in self._submitted[: self.max_lights]:
            sx, sy = camera.world_to_screen(light.x, light.y, width, height)
            radius = max(light.radius * zoom, 0.0)
            if radius <= 0.0 or light.intensity <= 0.0:
                continue
            if sx + radius < 0.0 or sx - radius > width:
                continue
            if sy + radius < 0.0 or sy - radius > height:
                continue

            shadow_start = len(shadow_segments)
            shadow_count = 0

            if self.shadows_enabled and light.cast_shadows:
                for segment in source_segments:
                    if shadow_count >= self.MAX_SEGMENTS_PER_LIGHT:
                        break
                    if len(shadow_segments) >= self.max_shadow_segments:
                        break
                    if segment.mask & light.shadow_mask == 0:
                        continue
                    if self._distance_to_segment(
                        float(sx),
                        float(sy),
                        segment.ax,
                        segment.ay,
                        segment.bx,
                        segment.by,
                    ) > radius:
                        continue
                    shadow_segments.append(
                        ScreenShadowSegment(
                            segment.ax,
                            segment.ay,
                            segment.bx,
                            segment.by,
                        )
                    )
                    shadow_count += 1

            lights.append(
                ScreenLight(
                    x=float(sx),
                    y=float(sy),
                    radius=float(radius),
                    intensity=float(light.intensity),
                    color=tuple(float(v) for v in light.color),
                    falloff=float(light.falloff),
                    shadow_start=shadow_start,
                    shadow_count=shadow_count,
                    shadow_strength=(
                        self._clamp01(light.shadow_strength)
                        if shadow_count
                        else 0.0
                    ),
                    shadow_softness=max(0.0, float(light.shadow_softness)),
                    shadow_color=tuple(self._clamp01(v) for v in light.shadow_color),
                )
            )

        return tuple(lights), tuple(shadow_segments)

    def screen_lights(
        self,
        camera,
        width: int,
        height: int,
    ) -> tuple[ScreenLight, ...]:
        lights, _ = self.build_screen_frame(camera, width, height)
        return lights

    def apply(self, post_process, camera, width: int, height: int) -> None:
        if not self.enabled:
            post_process.set_lighting(
                enabled=False,
                ambient_color=(1.0, 1.0, 1.0),
                ambient_intensity=1.0,
                lights=(),
                shadow_segments=(),
            )
            return

        lights, shadow_segments = self.build_screen_frame(
            camera,
            width,
            height,
        )

        post_process.enable()
        post_process.set_lighting(
            enabled=True,
            ambient_color=self.ambient_color,
            ambient_intensity=self.ambient_intensity,
            lights=lights,
            shadow_segments=shadow_segments,
        )
