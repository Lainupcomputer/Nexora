from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.ui_node import UINode


class Slider(UINode):
    """
    A horizontal or vertical slider UI component.

    Horizontal:
        min_value = left
        max_value = right

    Vertical:
        min_value = bottom
        max_value = top

    Keyboard:
        Left / Down
            Decrease value.

        Right / Up
            Increase value.

        Home
            Set minimum value.

        End
            Set maximum value.
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
        # Focus
        # --------------------------------------------------

        self.focusable = True

        # --------------------------------------------------
        # Value
        # --------------------------------------------------

        self.min_value: float = 0.0
        self.max_value: float = 1.0
        self.value: float = 0.0

        self.step: float = 0.1

        # --------------------------------------------------
        # Orientation
        # --------------------------------------------------

        self.orientation: str = "horizontal"

        # --------------------------------------------------
        # Size
        # --------------------------------------------------

        self.length: float = 200.0
        self.track_size: float = 8.0
        self.handle_size: float = 24.0

        # --------------------------------------------------
        # Colors
        # --------------------------------------------------

        self.track_background: tuple[int, int, int, int] = (
            32,
            34,
            37,
            255,
        )

        self.track_fill: tuple[int, int, int, int] = (
            45,
            120,
            70,
            255,
        )

        self.handle_background: tuple[int, int, int, int] = (
            180,
            180,
            180,
            255,
        )

        self.handle_hover_background: tuple[int, int, int, int] = (
            210,
            210,
            210,
            255,
        )

        self.handle_pressed_background: tuple[int, int, int, int] = (
            230,
            230,
            230,
            255,
        )

        self.handle_focus_background: tuple[int, int, int, int] = (
            200,
            215,
            255,
            255,
        )

        self.focus_border_color: tuple[int, int, int, int] = (
            80,
            140,
            220,
            255,
        )

        # --------------------------------------------------
        # State
        # --------------------------------------------------

        self.hovered: bool = False
        self.pressed: bool = False
        self._dragging: bool = False

        # --------------------------------------------------
        # Callback
        # --------------------------------------------------

        self.on_change: Callable[[float], None] | None = None

        # --------------------------------------------------
        # Children
        # --------------------------------------------------

        self.track = self.create_child(
            "Track",
            node_type=Panel,
        )

        self.fill = self.create_child(
            "Fill",
            node_type=Panel,
        )

        self.handle = self.create_child(
            "Handle",
            node_type=Panel,
        )

        self._sync_layout()
        self._sync_visuals()

    # ======================================================
    # Focus
    # ======================================================

    def on_focus(self) -> None:
        self._sync_visuals()

    def on_blur(self) -> None:
        self._dragging = False
        self.pressed = False

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
        *,
        emit: bool = True,
    ) -> None:
        """
        Set the slider value.
        """

        new_value = self._clamp_value(
            value
        )

        if new_value == self.value:
            return

        self.value = new_value

        if emit:
            callback = self.on_change

            if callback is not None:
                callback(
                    self.value
                )

        self._sync_layout()
        self._sync_visuals()

    def increase(
        self,
    ) -> None:
        """
        Increase the slider value by one step.
        """

        self.set_value(
            self.value + self.step
        )

    def decrease(
        self,
    ) -> None:
        """
        Decrease the slider value by one step.
        """

        self.set_value(
            self.value - self.step
        )

    @property
    def normalized_value(self) -> float:
        """
        Return the current value normalized to 0.0 - 1.0.
        """

        if self.max_value <= self.min_value:
            return 0.0

        return (
            self.value - self.min_value
        ) / (
            self.max_value - self.min_value
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
                "Slider orientation must be "
                "'horizontal' or 'vertical'."
            )

        return orientation == "vertical"

    # ======================================================
    # Layout
    # ======================================================

    def _sync_layout(self) -> None:
        """
        Synchronize slider child layout.
        """

        vertical = self._is_vertical()
        normalized = self.normalized_value

        # --------------------------------------------------
        # Horizontal
        # --------------------------------------------------

        if not vertical:
            self.size = (
                self.length,
                self.handle_size,
            )

            self.track.size = (
                self.length,
                self.track_size,
            )

            self.track.anchor = (
                0.0,
                0.5,
            )

            self.track.pivot = (
                0.0,
                0.5,
            )

            self.track.position = (
                self.length / 2.0,
                0.0,
            )

            fill_width = (
                self.length
                * normalized
            )

            self.fill.size = (
                fill_width,
                self.track_size,
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

            handle_x = (
                self.length
                * normalized
            )

            self.handle.size = (
                self.handle_size,
                self.handle_size,
            )

            self.handle.anchor = (
                0.0,
                0.5,
            )

            self.handle.pivot = (
                0.5,
                0.5,
            )

            self.handle.position = (
                handle_x,
                0.0,
            )

        # --------------------------------------------------
        # Vertical
        # --------------------------------------------------

        else:
            self.size = (
                self.handle_size,
                self.length,
            )

            self.track.size = (
                self.track_size,
                self.length,
            )

            self.track.anchor = (
                0.5,
                0.0,
            )

            self.track.pivot = (
                0.5,
                0.0,
            )

            self.track.position = (
                0.0,
                self.length / 2.0,
            )

            fill_height = (
                self.length
                * normalized
            )

            self.fill.size = (
                self.track_size,
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

            handle_y = (
                self.length
                * (1.0 - normalized)
            )

            self.handle.size = (
                self.handle_size,
                self.handle_size,
            )

            self.handle.anchor = (
                0.5,
                0.0,
            )

            self.handle.pivot = (
                0.5,
                0.5,
            )

            self.handle.position = (
                0.0,
                handle_y,
            )

    # ======================================================
    # Visuals
    # ======================================================

    def _sync_visuals(self) -> None:
        self.track.background = (
            self.track_background
        )

        self.track.border_width = 0.0
        self.track.border_radius = (
            self.track_size / 2.0
        )

        self.fill.background = (
            self.track_fill
        )

        self.fill.border_width = 0.0
        self.fill.border_radius = (
            self.track_size / 2.0
        )

        # --------------------------------------------------
        # Handle color
        # --------------------------------------------------

        if self.pressed:
            self.handle.background = (
                self.handle_pressed_background
            )

        elif self.hovered:
            self.handle.background = (
                self.handle_hover_background
            )

        elif self.focused:
            self.handle.background = (
                self.handle_focus_background
            )

        else:
            self.handle.background = (
                self.handle_background
            )

        # --------------------------------------------------
        # Focus border
        # --------------------------------------------------

        if self.focused:
            self.handle.border_width = 2.0
            self.handle.border_color = (
                self.focus_border_color
            )

        else:
            self.handle.border_width = 0.0

        self.handle.border_radius = (
            self.handle_size / 2.0
        )

    # ======================================================
    # Hit testing
    # ======================================================

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        rect_x, rect_y = (
            self.calculate_position()
        )

        width, height = self.size

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
    # Mouse -> value
    # ======================================================

    def _value_from_mouse(
        self,
        x: float,
        y: float,
    ) -> float:
        """
        Convert a mouse position into a slider value.
        """

        rect_x, rect_y = (
            self.calculate_position()
        )

        if self.length <= 0.0:
            return self.min_value

        vertical = self._is_vertical()

        if not vertical:
            left = (
                rect_x
                - self.length / 2.0
            )

            normalized = (
                x - left
            ) / self.length

        else:
            top = (
                rect_y
                - self.length / 2.0
            )

            normalized = (
                y - top
            ) / self.length

            normalized = (
                1.0 - normalized
            )

        normalized = max(
            0.0,
            min(
                1.0,
                normalized,
            ),
        )

        return (
            self.min_value
            + normalized
            * (
                self.max_value
                - self.min_value
            )
        )

    # ======================================================
    # Keyboard
    # ======================================================

    def _handle_keyboard(
        self,
        ui_input,
    ) -> None:
        if not self.focused:
            return

        vertical = self._is_vertical()

        # --------------------------------------------------
        # Decrease
        # --------------------------------------------------

        decrease = (
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_LEFT
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_DOWN
            )
        )

        # --------------------------------------------------
        # Increase
        # --------------------------------------------------

        increase = (
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_RIGHT
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_UP
            )
        )

        if decrease:
            self.decrease()

        if increase:
            self.increase()

        # --------------------------------------------------
        # Minimum
        # --------------------------------------------------

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_HOME
        ):
            self.set_value(
                self.min_value
            )

        # --------------------------------------------------
        # Maximum
        # --------------------------------------------------

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_END
        ):
            self.set_value(
                self.max_value
            )

    # ======================================================
    # Input
    # ======================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        if (
            not self.visible
            or not self.enabled
        ):
            self.hovered = False
            self.pressed = False
            self._dragging = False

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
        # Mouse
        # --------------------------------------------------

        if ui_input.mouse_left_pressed:
            if self.hovered:
                self._dragging = True

                self.set_value(
                    self._value_from_mouse(
                        mouse_x,
                        mouse_y,
                    )
                )

        if self._dragging:
            if ui_input.mouse_left_down:
                self.set_value(
                    self._value_from_mouse(
                        mouse_x,
                        mouse_y,
                    )
                )

        if ui_input.mouse_left_released:
            self._dragging = False

        self.pressed = self._dragging

        # --------------------------------------------------
        # Keyboard
        # --------------------------------------------------

        self._handle_keyboard(
            ui_input
        )

        self._sync_layout()
        self._sync_visuals()

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

        self.track.render(
            renderer
        )

        self.fill.render(
            renderer
        )

        self.handle.render(
            renderer
        )