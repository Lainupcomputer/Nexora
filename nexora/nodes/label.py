from __future__ import annotations

from nexora.nodes.ui_node import UINode


class Label(UINode):
    """
    A UI text label.

    Positioning is handled by UINode:
        - anchor
        - position
        - parent hierarchy
        - pivot
    """

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.text: str = ""

        self.scale: float = 1.0
        self.rotation: float = 0.0

    def render(self, renderer) -> None:
        if not self.visible:
            return

        if not self.text:
            super().render(renderer)
            return

        x, y = self.calculate_position()

        width, height = renderer.text_measure(
            self.text,
            scale=self.scale,
        )

        baseline = renderer.text_baseline(
            scale=self.scale,
        )

        x -= width * self.pivot[0]
        y -= height * self.pivot[1]
        y += baseline

        renderer.text(
            self.text,
            x,
            y,
            rotation=self.rotation,
            scale=self.scale,
        )

        super().render(renderer)