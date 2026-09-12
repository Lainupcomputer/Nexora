from __future__ import annotations

from collections.abc import Callable

from nexora.nodes.label import Label
from nexora.nodes.panel import Panel
from nexora.nodes.ui_node import UINode


class RadioButton(UINode):
    """
    A radio button UI component.

    Radio buttons can be placed into a shared group.
    Only one radio button in a group can be selected.
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

        self.selected: bool = False

        self.hovered: bool = False
        self.pressed: bool = False

        self._press_started_inside: bool = False

        # --------------------------------------------------
        # Group
        # --------------------------------------------------

        self.group: RadioButtonGroup | None = None

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

        self.selected_background: tuple[int, int, int, int] = (
            45,
            120,
            70,
            255,
        )

        self.selected_hover_background: tuple[int, int, int, int] = (
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

        self.selected_border_color: tuple[int, int, int, int] = (
            100,
            220,
            130,
            255,
        )

        self.border_width: float = 2.0

        self.border_radius: float = 16.0

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

        self.label = self.create_child(
            "Label",
            node_type=Label,
        )

        self._sync_layout()
        self._sync_visuals()

    # ======================================================
    # Group
    # ======================================================

    def set_group(
        self,
        group: RadioButtonGroup | None,
    ) -> None:
        """
        Assign this radio button to a group.
        """

        if self.group is group:
            return

        if self.group is not None:
            self.group.remove(self)

        self.group = group

        if self.group is not None:
            self.group.add(self)

    # ======================================================
    # Selection
    # ======================================================

    def set_selected(
        self,
        selected: bool,
    ) -> None:
        """
        Set the selected state.

        Selecting a radio button automatically deselects
        the other buttons in the same group.
        """

        selected = bool(selected)

        if selected:
            if self.group is not None:
                self.group.select(self)
            else:
                self.selected = True

        else:
            self.selected = False

        self._sync_visuals()

    # ======================================================
    # Size
    # ======================================================

    @property
    def content_size(self) -> tuple[float, float]:
        """
        Return the size of the complete radio button.
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
        Synchronize the radio button child layout.
        """

        self.size = self.content_size

        # --------------------------------------------------
        # Circle
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
        Synchronize the radio button appearance.
        """

        if self.selected:
            if self.hovered:
                self.box.background = (
                    self.selected_hover_background
                )
            else:
                self.box.background = (
                    self.selected_background
                )

            self.box.border_color = (
                self.selected_border_color
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

    # ======================================================
    # Hit testing
    # ======================================================

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        """
        Check whether a point is inside the radio button.
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
            should_select = (
                self._press_started_inside
                and self.hovered
            )

            self.pressed = False
            self._press_started_inside = False

            if should_select:
                if self.group is not None:
                    self.group.select(self)
                elif not self.selected:
                    self.selected = True

                    callback = self.on_change

                    if callback is not None:
                        callback(True)

        self._sync_visuals()

    # ======================================================
    # Render
    # ======================================================

    def render(
        self,
        renderer,
    ) -> None:
        """
        Render the radio button.
        """

        if not self.visible:
            return

        self._sync_layout()
        self._sync_visuals()

        self.box.render(renderer)
        self.label.render(renderer)


class RadioButtonGroup:
    """
    Group of radio buttons.

    Only one button in the group can be selected at a time.
    """

    def __init__(self) -> None:
        self.buttons: list[RadioButton] = []

    def add(
        self,
        button: RadioButton,
    ) -> None:
        """
        Add a radio button to the group.
        """

        if button not in self.buttons:
            self.buttons.append(button)

    def remove(
        self,
        button: RadioButton,
    ) -> None:
        """
        Remove a radio button from the group.
        """

        if button in self.buttons:
            self.buttons.remove(button)

    def select(
        self,
        button: RadioButton,
    ) -> None:
        """
        Select one button and deselect all others.
        """

        if button not in self.buttons:
            self.add(button)

        for other in self.buttons:
            if other is button:
                if not other.selected:
                    other.selected = True

                    callback = other.on_change

                    if callback is not None:
                        callback(True)

            elif other.selected:
                other.selected = False

                callback = other.on_change

                if callback is not None:
                    callback(False)

    @property
    def selected(
        self,
    ) -> RadioButton | None:
        """
        Return the currently selected radio button.
        """

        for button in self.buttons:
            if button.selected:
                return button

        return None