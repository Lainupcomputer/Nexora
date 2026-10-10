from __future__ import annotations

from dataclasses import dataclass

@dataclass(slots=True)
class EditorViewportState:
    """Pan/zoom state for the editor's 2D viewport."""

    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    min_zoom: float = 0.10
    max_zoom: float = 8.0

    def clamp_zoom(self, value: float) -> float:
        return max(
            self.min_zoom,
            min(
                self.max_zoom,
                float(value),
            ),
        )

    def world_to_screen(
        self,
        world_x: float,
        world_y: float,
        center_x: float,
        center_y: float,
    ) -> tuple[float, float]:
        return (
            center_x + (float(world_x) - self.x) * self.zoom,
            center_y + (float(world_y) - self.y) * self.zoom,
        )

    def screen_to_world(
        self,
        screen_x: float,
        screen_y: float,
        center_x: float,
        center_y: float,
    ) -> tuple[float, float]:
        zoom = max(self.zoom, 1e-9)
        return (
            self.x + (float(screen_x) - center_x) / zoom,
            self.y + (float(screen_y) - center_y) / zoom,
        )

    def pan_screen_delta(
        self,
        dx: float,
        dy: float,
    ) -> None:
        zoom = max(self.zoom, 1e-9)
        self.x -= float(dx) / zoom
        self.y -= float(dy) / zoom

    def zoom_at(
        self,
        screen_x: float,
        screen_y: float,
        center_x: float,
        center_y: float,
        factor: float,
    ) -> None:
        before_x, before_y = self.screen_to_world(
            screen_x,
            screen_y,
            center_x,
            center_y,
        )

        self.zoom = self.clamp_zoom(
            self.zoom * float(factor)
        )

        self.x = (
            before_x
            - (screen_x - center_x) / self.zoom
        )
        self.y = (
            before_y
            - (screen_y - center_y) / self.zoom
        )

    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0
