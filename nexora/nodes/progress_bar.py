from __future__ import annotations

from nexora.nodes.panel import Panel
from nexora.nodes.ui_node import UINode


class ProgressBar(UINode):
    """
    A horizontal or vertical progress bar.

    Horizontal:
        min_value = left
        max_value = right

    Vertical:
        min_value = bottom
        max_value = top
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

        # --------------------------------------------------
        # Value
        # --------------------------------------------------

        self.min_value: float = 0.0
        self.max_value: float = 100.0
        self.value: float = 0.0

        # --------------------------------------------------
        # Orientation
        # --------------------------------------------------

        self.orientation: str = "horizontal"

        # --------------------------------------------------
        # Size
        # --------------------------------------------------

        self.length: float = 300.0
        self.thickness: float = 24.0

        # --------------------------------------------------
        # Appearance
        # --------------------------------------------------

        self.background: tuple[int, int, int, int] = (
            32,
            34,
            37,
            255,
        )

        self.fill_color: tuple[int, int, int, int] = (
            45,
            120,
            70,
            255,
        )

        self.border_color: tuple[int, int, int, int] = (
            70,
            70,
            75,
            255,
        )

        self.border_width: float = 2.0
        self.border_radius: float = 6.0

        # --------------------------------------------------
        # Children
        # --------------------------------------------------

        self.background_panel = self.create_child(
            "Background",
            node_type=Panel,
        )

        self.fill = self.create_child(
            "Fill",
            node_type=Panel,
        )

        self._sync_layout()
        self._sync_visuals()

    # ======================================================
    # Value
    # ======================================================

    def _clamp_value(
        self,
        value: float,
    ) -> float:
        if self.max_value <= self.min_value:
            return self.min_value

        return max(
            self.min_value,
            min(
                self.max_value,
                float(value),
            ),
        )

    def set_value(
        self,
        value: float,
    ) -> None:
        """
        Set the progress value.
        """

        self.value = self._clamp_value(
            value,
        )

    @property
    def normalized_value(self) -> float:
        """
        Return the current progress as 0.0 - 1.0.
        """

        if self.max_value <= self.min_value:
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                (
                    self.value
                    - self.min_value
                )
                / (
                    self.max_value
                    - self.min_value
                ),
            ),
        )

    # ======================================================
    # Orientation
    # ======================================================

    def _is_vertical(self) -> bool:
        orientation = self.orientation.lower()

        if orientation not in (
            "horizontal",
            "vertical",
        ):
            raise ValueError(
                "ProgressBar orientation must be "
                "'horizontal' or 'vertical'."
            )

        return orientation == "vertical"

    # ======================================================
    # Layout
    # ======================================================

    def _sync_layout(self) -> None:
        vertical = self._is_vertical()
        normalized = self.normalized_value

        # --------------------------------------------------
        # Horizontal
        # --------------------------------------------------

        if not vertical:
            self.size = (
                self.length,
                self.thickness,
            )

            # Background
            self.background_panel.size = (
                self.length,
                self.thickness,
            )

            self.background_panel.anchor = (
                0.0,
                0.5,
            )

            self.background_panel.pivot = (
                0.0,
                0.5,
            )

            self.background_panel.position = (
                self.length / 2.0,
                0.0,
            )

            # Fill
            fill_width = (
                self.length
                * normalized
            )

            self.fill.size = (
                fill_width,
                self.thickness,
            )

            self.fill.anchor = (
                0.0,
                0.5,
            )

            self.fill.pivot = (
                0.0,
                0.5,
            )

            self.fill.position = (
                fill_width / 2.0,
                0.0,
            )

        # --------------------------------------------------
        # Vertical
        # --------------------------------------------------

        else:
            self.size = (
                self.thickness,
                self.length,
            )

            # Background
            self.background_panel.size = (
                self.thickness,
                self.length,
            )

            self.background_panel.anchor = (
                0.5,
                0.0,
            )

            self.background_panel.pivot = (
                0.5,
                0.0,
            )

            self.background_panel.position = (
                0.0,
                self.length / 2.0,
            )

            # Fill
            fill_height = (
                self.length
                * normalized
            )

            self.fill.size = (
                self.thickness,
                fill_height,
            )

            self.fill.anchor = (
                0.5,
                1.0,
            )

            self.fill.pivot = (
                0.5,
                1.0,
            )

            self.fill.position = (
                0.0,
                -fill_height / 2.0,
            )

    # ======================================================
    # Visuals
    # ======================================================

    def _sync_visuals(self) -> None:
        # --------------------------------------------------
        # Background
        # --------------------------------------------------

        self.background_panel.background = (
            self.background
        )

        self.background_panel.border_color = (
            self.border_color
        )

        self.background_panel.border_width = (
            self.border_width
        )

        self.background_panel.border_radius = (
            self.border_radius
        )

        # --------------------------------------------------
        # Fill
        # --------------------------------------------------

        self.fill.background = (
            self.fill_color
        )

        self.fill.border_width = 0.0

        self.fill.border_radius = (
            self.border_radius
        )

    # ======================================================
    # Render
    # ======================================================

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._sync_layout()
        self._sync_visuals()

        self.background_panel.render(
            renderer,
        )

        self.fill.render(
            renderer,
        )