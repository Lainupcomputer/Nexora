from __future__ import annotations


class UIInput:
    """
    Input state used by Nexora's UI system.

    This class does not depend on SDL events.

    The application / engine loop feeds the current mouse and
    keyboard state into this object.
    """

    def __init__(self) -> None:
        # --------------------------------------------------------------
        # Mouse
        # --------------------------------------------------------------

        self.mouse_position: tuple[float, float] = (
            0.0,
            0.0,
        )

        self.mouse_left_down: bool = False
        self.mouse_left_pressed: bool = False
        self.mouse_left_released: bool = False

        # --------------------------------------------------------------
        # Mouse wheel
        # --------------------------------------------------------------

        self.mouse_wheel_x: float = 0.0
        self.mouse_wheel_y: float = 0.0

        # --------------------------------------------------------------
        # Keyboard
        # --------------------------------------------------------------

        self.keys_down: frozenset[int] = frozenset()
        self.keys_pressed: frozenset[int] = frozenset()
        self.keys_released: frozenset[int] = frozenset()

        # --------------------------------------------------------------
        # Text input
        # --------------------------------------------------------------

        self.text_input: tuple[str, ...] = ()

    # ------------------------------------------------------------------
    # Frame
    # ------------------------------------------------------------------

    def begin_frame(self) -> None:
        self.mouse_left_pressed = False
        self.mouse_left_released = False

        self.mouse_wheel_x = 0.0
        self.mouse_wheel_y = 0.0

        self.keys_pressed = frozenset()
        self.keys_released = frozenset()

        self.text_input = ()

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def set_mouse_position(
        self,
        x: float,
        y: float,
    ) -> None:
        self.mouse_position = (
            float(x),
            float(y),
        )

    def set_mouse_left(
        self,
        down: bool,
    ) -> None:
        down = bool(down)

        if down and not self.mouse_left_down:
            self.mouse_left_pressed = True

        elif not down and self.mouse_left_down:
            self.mouse_left_released = True

        self.mouse_left_down = down

    def update_mouse(
        self,
        position: tuple[float, float],
        down: bool,
        pressed: bool,
        released: bool,
        wheel_x: float = 0.0,
        wheel_y: float = 0.0,
    ) -> None:
        self.mouse_position = (
            float(position[0]),
            float(position[1]),
        )

        self.mouse_left_down = bool(down)
        self.mouse_left_pressed = bool(pressed)
        self.mouse_left_released = bool(released)

        self.mouse_wheel_x = float(wheel_x)
        self.mouse_wheel_y = float(wheel_y)

    def update_wheel(
        self,
        x: float,
        y: float,
    ) -> None:
        self.mouse_wheel_x = float(x)
        self.mouse_wheel_y = float(y)

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def update_keyboard(
        self,
        keys_down,
        keys_pressed,
        keys_released,
    ) -> None:
        self.keys_down = frozenset(keys_down)
        self.keys_pressed = frozenset(keys_pressed)
        self.keys_released = frozenset(keys_released)

    def key_down(
        self,
        key: int,
    ) -> bool:
        return key in self.keys_down

    def key_pressed(
        self,
        key: int,
    ) -> bool:
        return key in self.keys_pressed

    def key_released(
        self,
        key: int,
    ) -> bool:
        return key in self.keys_released

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    def update_text_input(
        self,
        text_input,
    ) -> None:
        self.text_input = tuple(
            text_input,
        )