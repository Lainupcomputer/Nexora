from __future__ import annotations

from collections.abc import Callable

from nexora.nodes.label import Label
from nexora.nodes.panel import Panel


class Button(Panel):
    """
    A clickable UI button.
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

        # ----------------------------------------------------------
        # Text
        # ----------------------------------------------------------

        self.text: str = ""

        self.text_scale: float = 1.0

        self.text_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
            255,
            255,
            255,
            255,
        )

        # ----------------------------------------------------------
        # Visual states
        # ----------------------------------------------------------

        self.hovered: bool = False
        self.pressed: bool = False

        self.normal_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            32,
            34,
            37,
            255,
        )

        self.hover_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            45,
            48,
            52,
            255,
        )

        self.pressed_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            25,
            27,
            30,
            255,
        )

        self.disabled_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            20,
            21,
            23,
            255,
        )

        self.disabled_text_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
            120,
            120,
            120,
            255,
        )

        # ----------------------------------------------------------
        # Click state
        # ----------------------------------------------------------

        self._press_started_inside: bool = False

        self.on_click: Callable[[], None] | None = None

        # ----------------------------------------------------------
        # Internal label
        # ----------------------------------------------------------

        self._label = Label(
            f"{name}_Label",
            world,
        )

        self.add_child(
            self._label,
        )

        self._sync_label()

    # ==============================================================
    # State
    # ==============================================================

    def _sync_label(self) -> None:
        self._label.text = self.text
        self._label.scale = self.text_scale

        self._label.anchor = (
            0.5,
            0.5,
        )

        self._label.pivot = (
            0.5,
            0.5,
        )

        self._label.position = (
            0.0,
            0.0,
        )

    def _sync_background(self) -> None:
        if not self.enabled:
            self.background = (
                self.disabled_background
            )

        elif self.pressed:
            self.background = (
                self.pressed_background
            )

        elif self.hovered:
            self.background = (
                self.hover_background
            )

        else:
            self.background = (
                self.normal_background
            )

    # ==============================================================
    # Rendering
    # ==============================================================

    def render(self, renderer) -> None:
        if not self.visible:
            return

        self._sync_label()
        self._sync_background()

        super().render(
            renderer,
        )

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        """
        Update the button's input state.

        A click is only generated when the mouse button was pressed
        while the pointer was inside the button and released while
        the pointer is still inside the button.
        """

        if not self.visible or not self.enabled:
            self.hovered = False
            self.pressed = False
            self._press_started_inside = False
            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self.hovered = self.contains_point(
            mouse_x,
            mouse_y,
        )

        # ----------------------------------------------------------
        # Mouse button pressed
        # ----------------------------------------------------------

        if ui_input.mouse_left_pressed:
            self._press_started_inside = (
                self.hovered
            )

        # ----------------------------------------------------------
        # Mouse button held
        # ----------------------------------------------------------

        self.pressed = (
            self._press_started_inside
            and ui_input.mouse_left_down
            and self.hovered
        )

        # ----------------------------------------------------------
        # Mouse button released
        # ----------------------------------------------------------

        if ui_input.mouse_left_released:
            should_click = (
                self._press_started_inside
                and self.hovered
            )

            self.pressed = False
            self._press_started_inside = False

            if should_click:
                callback = self.on_click

                if callback is not None:
                    callback()