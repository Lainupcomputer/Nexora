from __future__ import annotations

import math

from nexora.lighting import OccluderSnapshot
from nexora.nodes.node import Node


class LightOccluder2D(Node):
    """Polygon/segment node that blocks Light2D shadow rays."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.points: list[tuple[float, float]] = [
            (-32.0, -32.0),
            (32.0, -32.0),
            (32.0, 32.0),
            (-32.0, 32.0),
        ]
        self.closed = True
        self.occluder_enabled = True
        self.occluder_mask = 0xFFFFFFFF
        self.debug_draw = False
        self.debug_layer = 100_010

    def set_polygon(self, points) -> None:
        converted = [(float(x), float(y)) for x, y in points]
        if len(converted) < 2:
            raise ValueError("LightOccluder2D requires at least two points")
        self.points = converted

    def set_segment(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> None:
        self.points = [
            (float(start[0]), float(start[1])),
            (float(end[0]), float(end[1])),
        ]
        self.closed = False

    def _world_points(self) -> tuple[tuple[float, float], ...]:
        origin_x, origin_y = self.world_position
        scale_x, scale_y = self.world_scale
        angle = math.radians(self.world_rotation)
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)

        result: list[tuple[float, float]] = []
        for local_x, local_y in self.points:
            scaled_x = local_x * scale_x
            scaled_y = local_y * scale_y
            rotated_x = scaled_x * cos_angle - scaled_y * sin_angle
            rotated_y = scaled_x * sin_angle + scaled_y * cos_angle
            result.append((origin_x + rotated_x, origin_y + rotated_y))
        return tuple(result)

    def snapshot(self) -> OccluderSnapshot:
        return OccluderSnapshot(
            points=self._world_points(),
            mask=int(self.occluder_mask),
            closed=bool(self.closed),
        )

    def render(self, renderer, interpolation: float) -> None:
        del interpolation
        if not self.occluder_enabled or not self.visible:
            return

        snapshot = self.snapshot()
        renderer.lighting.submit_occluder(snapshot)

        if not self.debug_draw:
            return

        for (ax, ay), (bx, by) in snapshot.segments():
            renderer.line(
                ax,
                ay,
                bx,
                by,
                width=3.0,
                color=(1.0, 0.2, 0.8, 0.9),
                layer=int(self.debug_layer),
            )
