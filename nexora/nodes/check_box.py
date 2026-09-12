from __future__ import annotations

from collections.abc import Callable

from nexora.nodes.label import Label
from nexora.nodes.panel import Panel
from nexora.nodes.ui_node import UINode


class CheckBox(UINode):
    """
    A checkbox UI component.

    The checkbox consists of:
        - a rectangular box
        - a checkmark
        - a text label

    Clicking the checkbox toggles the `checked` state.
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
        # State
        # --------------------------------------------------

        self.checked: bool = False

        self.hovered: bool = False
        self.pressed: bool = False

        self._press_started_inside: bool = False

        # --------------------------------------------------
        # Appearance
        # --------------------------------------------------

        self.box_size: tuple[float, float] = (
            32.0,
            32.0,
        )

        self.spacing: float = 10.0

        self.text: str = ""

        self.text_scale: float = 1.0

        # --------------------------------------------------
        # Colors
        # --------------------------------------------------

        self.background: tuple[int, int, int, int] = (
            32,
            34,
            37,
            255,
        )

        self.hover_background: tuple[int, int, int, int] = (
            55,
            58,
            64,
            255,
        )

        self.checked_background: tuple[int, int, int, int] = (
            45,
            120,
            70,
            255,
        )

        self.checked_hover_background: tuple[int, int, int, int] = (
            60,
            145,
            85,
            255,
        )

        self.border_color: tuple[int, int, int, int] = (
            100,
            100,
            100,
            255,
        )

        self.checked_border_color: tuple[int, int, int, int] = (
            100,
            220,
            130,
            255,
        )

        self.border_width: float = 2.0

        self.border_radius: float = 4.0

        # --------------------------------------------------
        # Callback
        # --------------------------------------------------

        self.on_change: Callable[[bool], None] | None = None

        # --------------------------------------------------
        # Children
        # --------------------------------------------------

        self.box = self.create_child(
            "Box",
            node_type=Panel,
        )

        self.checkmark = self.create_child(
            "Checkmark",
            node_type=Label,
        )

        self.label = self.create_child(
            "Label",
            node_type=Label,
        )

        self._sync_layout()
        self._sync_visuals()

    # ======================================================
    # Size
    # ======================================================

    @property
    def content_size(self) -> tuple[float, float]:
        """
        Return the size of the complete checkbox.
        """

        label_width = max(
            0.0,
            len(self.text)
            * 16.0
            * self.text_scale,
        )

        label_height = (
            32.0
            * self.text_scale
        )

        return (
            self.box_size[0]
            + self.spacing
            + label_width,
            max(
                self.box_size[1],
                label_height,
            ),
        )

    # ======================================================
    # Layout
    # ======================================================

    def _sync_layout(self) -> None:
        """
        Synchronize the checkbox child layout.
        """

        self.size = self.content_size

        # --------------------------------------------------
        # Box
        # --------------------------------------------------

        self.box.size = self.box_size

        self.box.anchor = (
            0.0,
            0.5,
        )

        self.box.pivot = (
            0.0,
            0.5,
        )

        self.box.position = (
            0.0,
            0.0,
        )

        # --------------------------------------------------
        # Checkmark
        # --------------------------------------------------

        self.checkmark.text = "✓"

        self.checkmark.scale = 0.9

        self.checkmark.anchor = (
            0.5,
            0.5,
        )

        self.checkmark.pivot = (
            0.5,
            0.5,
        )

        self.checkmark.position = (
            self.box_size[0] / 2.0,
            0.0,
        )

        # --------------------------------------------------
        # Label
        # --------------------------------------------------

        self.label.text = self.text
        self.label.scale = self.text_scale

        self.label.anchor = (
            0.0,
            0.5,
        )

        self.label.pivot = (
            0.0,
            0.5,
        )

        self.label.position = (
            self.box_size[0]
            + self.spacing,
            0.0,
        )

    # ======================================================
    # Visual state
    # ======================================================

    def _sync_visuals(self) -> None:
        """
        Synchronize the checkbox appearance.
        """

        if self.checked:
            if self.hovered:
                self.box.background = (
                    self.checked_hover_background
                )
            else:
                self.box.background = (
                    self.checked_background
                )

            self.box.border_color = (
                self.checked_border_color
            )

        else:
            if self.hovered:
                self.box.background = (
                    self.hover_background
                )
            else:
                self.box.background = (
                    self.background
                )

            self.box.border_color = (
                self.border_color
            )

        self.box.border_width = (
            self.border_width
        )

        self.box.border_radius = (
            self.border_radius
        )

        self.checkmark.visible = self.checked

    # ======================================================
    # Hit testing
    # ======================================================

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        """
        Check whether a point is inside the checkbox.
        """

        rect_x, rect_y = (
            self.calculate_position()
        )

        width, height = (
            self.content_size
        )

        left = (
            rect_x
            - width * self.pivot[0]
        )

        top = (
            rect_y
            - height * self.pivot[1]
        )

        right = left + width
        bottom = top + height

        return (
            left <= x <= right
            and
            top <= y <= bottom
        )

    # ======================================================
    # Input
    # ======================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        """
        Process mouse input.
        """

        if not self.visible or not self.enabled:
            self.hovered = False
            self.pressed = False
            self._press_started_inside = False

            self._sync_visuals()

            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self.hovered = self.contains_point(
            mouse_x,
            mouse_y,
        )

        # --------------------------------------------------
        # Mouse press
        # --------------------------------------------------

        if ui_input.mouse_left_pressed:
            self._press_started_inside = (
                self.hovered
            )

        self.pressed = (
            self._press_started_inside
            and ui_input.mouse_left_down
            and self.hovered
        )

        # --------------------------------------------------
        # Mouse release
        # --------------------------------------------------

        if ui_input.mouse_left_released:
            should_toggle = (
                self._press_started_inside
                and self.hovered
            )

            self.pressed = False
            self._press_started_inside = False

            if should_toggle:
                self.checked = not self.checked

                callback = self.on_change

                if callback is not None:
                    callback(self.checked)

        self._sync_visuals()

    # ======================================================
    # Render
    # ======================================================

    def render(
        self,
        renderer,
    ) -> None:
        """
        Render the checkbox.
        """

        if not self.visible:
            return

        self._sync_layout()
        self._sync_visuals()

        self.box.render(renderer)
        self.checkmark.render(renderer)
        self.label.render(renderer)