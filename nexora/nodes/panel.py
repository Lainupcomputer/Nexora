from __future__ import annotations

from nexora.nodes.ui_node import UINode


class Panel(UINode):
    """A rectangular UI container."""

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(name, world)

        self.background: tuple[int, int, int, int] = (
            32,
            34,
            37,
            255,
        )

        self.border_color: tuple[int, int, int, int] = (
            0,
            0,
            0,
            0,
        )

        self.border_width: float = 0.0
        self.border_radius: float = 0.0

    @staticmethod
    def _color_to_float(
        color: tuple[int, int, int, int],
    ) -> tuple[float, float, float, float]:
        return tuple(
            channel / 255.0
            for channel in color
        )

    def render(self, renderer) -> None:
        if not self.visible:
            return

        x, y = self.calculate_position()

        width, height = self.size

        if self.border_width > 0.0:
            border_width = min(
                self.border_width,
                width / 2.0,
                height / 2.0,
            )

            # --------------------------------------------------
            # Outer border
            # --------------------------------------------------

            renderer.rect(
                x,
                y,
                width,
                height,
                color=self._color_to_float(
                    self.border_color,
                ),
                radius=self.border_radius,
            )

            # --------------------------------------------------
            # Inner background
            # --------------------------------------------------

            inner_radius = max(
                self.border_radius - border_width,
                0.0,
            )

            renderer.rect(
                x,
                y,
                width - border_width * 2.0,
                height - border_width * 2.0,
                color=self._color_to_float(
                    self.background,
                ),
                radius=inner_radius,
            )

        else:
            # --------------------------------------------------
            # Background without border
            # --------------------------------------------------

            renderer.rect(
                x,
                y,
                width,
                height,
                color=self._color_to_float(
                    self.background,
                ),
                radius=self.border_radius,
            )

        super().render(renderer)

