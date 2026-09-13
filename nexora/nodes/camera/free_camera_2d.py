from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes.camera.camera_2d import Camera2D


if TYPE_CHECKING:
    from nexora.input.input import InputManager
    from nexora.rendering.renderer import Renderer


class FreeCamera2D(Camera2D):
    """
    Freely controllable 2D camera.

    Supports:

        - keyboard movement
        - movement boost
        - mouse drag panning
        - mouse wheel zoom

    Typical use cases:

        - map editors
        - debug cameras
        - spectator cameras
        - strategy games
        - development tools
    """

    def __init__(
        self,
        name: str,
        world,
        renderer: Renderer,
        input_manager: InputManager,
    ) -> None:
        super().__init__(
            name,
            world,
            renderer,
        )

        self.input = input_manager

        # ======================================================
        # Movement
        # ======================================================

        self.move_speed: float = 700.0

        self.boost_multiplier: float = 2.5

        # ======================================================
        # Zoom
        # ======================================================

        self.mouse_zoom_enabled: bool = True

        self.mouse_zoom_speed: float = 0.15

        # ======================================================
        # Mouse drag
        # ======================================================

        self.drag_enabled: bool = True

        self.drag_button: str = "middle"

        self.drag_speed: float = 1.0

        self._dragging: bool = False

        # ======================================================
        # Input bindings
        # ======================================================

        self.move_left_action = "camera_left"
        self.move_right_action = "camera_right"
        self.move_up_action = "camera_up"
        self.move_down_action = "camera_down"

        self.boost_action = "camera_boost"

    # ==========================================================
    # Configuration
    # ==========================================================

    def set_move_speed(
        self,
        speed: float,
    ) -> None:
        speed = float(speed)

        if speed < 0.0:
            raise ValueError(
                "Camera move speed cannot be negative."
            )

        self.move_speed = speed

    def set_boost_multiplier(
        self,
        multiplier: float,
    ) -> None:
        multiplier = float(multiplier)

        if multiplier < 0.0:
            raise ValueError(
                "Camera boost multiplier cannot be negative."
            )

        self.boost_multiplier = multiplier

    def set_mouse_zoom_speed(
        self,
        speed: float,
    ) -> None:
        speed = float(speed)

        if speed < 0.0:
            raise ValueError(
                "Mouse zoom speed cannot be negative."
            )

        self.mouse_zoom_speed = speed

    def set_drag_speed(
        self,
        speed: float,
    ) -> None:
        speed = float(speed)

        if speed < 0.0:
            raise ValueError(
                "Camera drag speed cannot be negative."
            )

        self.drag_speed = speed

    # ==========================================================
    # Keyboard movement
    # ==========================================================

    def _update_keyboard(
        self,
        delta_time: float,
    ) -> None:
        move_x = 0.0
        move_y = 0.0

        if self.input.action(
            self.move_left_action
        ).down:
            move_x -= 1.0

        if self.input.action(
            self.move_right_action
        ).down:
            move_x += 1.0

        if self.input.action(
            self.move_up_action
        ).down:
            move_y -= 1.0

        if self.input.action(
            self.move_down_action
        ).down:
            move_y += 1.0

        # ------------------------------------------------------
        # Normalize diagonal movement
        # ------------------------------------------------------

        if (
            move_x != 0.0
            and move_y != 0.0
        ):
            diagonal = 0.70710678118

            move_x *= diagonal
            move_y *= diagonal

        speed = self.move_speed

        if self.input.action(
            self.boost_action
        ).down:
            speed *= self.boost_multiplier

        move_x *= speed * delta_time
        move_y *= speed * delta_time

        if (
            move_x != 0.0
            or move_y != 0.0
        ):
            self.move(
                move_x,
                move_y,
            )

    # ==========================================================
    # Mouse drag
    # ==========================================================

    def _update_mouse_drag(
        self,
    ) -> None:
        if not self.drag_enabled:
            self._dragging = False
            return

        if self.input.mouse_down(
            self.drag_button
        ):
            self._dragging = True

            delta_x, delta_y = (
                self.input.mouse_delta
            )

            delta_x = float(
                delta_x
            )

            delta_y = float(
                delta_y
            )

            if (
                delta_x != 0.0
                or delta_y != 0.0
            ):
                zoom = max(
                    self.zoom,
                    0.0001,
                )

                self.move(
                    (
                        -delta_x
                        / zoom
                        * self.drag_speed
                    ),
                    (
                        -delta_y
                        / zoom
                        * self.drag_speed
                    ),
                )

        else:
            self._dragging = False

    # ==========================================================
    # Mouse zoom
    # ==========================================================

    def _update_mouse_zoom(
        self,
    ) -> None:
        if not self.mouse_zoom_enabled:
            return

        _, wheel_y = (
            self.input.wheel
        )

        wheel_y = float(
            wheel_y
        )

        if wheel_y == 0.0:
            return

        zoom_delta = (
            wheel_y
            * self.mouse_zoom_speed
        )

        self.camera.zoom_by(
            zoom_delta
        )

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self.active:
            return

        self._update_keyboard(
            delta_time
        )

        self._update_mouse_drag()

        self._update_mouse_zoom()

        super().update(
            delta_time
        )