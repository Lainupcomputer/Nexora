from __future__ import annotations

import sdl3

from nexora import Game


class InputTestGame(Game):
    """
    Nexora public input API test.

    Controls:
        A / D       Keyboard actions
        SPACE       Jump action
        Left Mouse  Fire action
        ESC         Exit
    """

    def __init__(self):
        super().__init__(
            title="Nexora - Input Test",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            window_mode="windowed",
            vsync=True,
        )

        self._last_output = None

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self):
        # ------------------------------------------------------
        # Keyboard bindings
        # ------------------------------------------------------

        self.input.bind(
            "left",
            "A",
        )

        self.input.bind(
            "right",
            "D",
        )

        self.input.bind(
            "jump",
            "SPACE",
        )

        # ------------------------------------------------------
        # Mouse bindings
        # ------------------------------------------------------

        self.input.bind_mouse(
            "fire",
            "left",
        )

        print()
        print("=" * 50)
        print(" Nexora Input System Test")
        print("=" * 50)
        print()
        print("Controls:")
        print("  A          = Left")
        print("  D          = Right")
        print("  SPACE      = Jump")
        print("  Left Mouse = Fire")
        print("  ESC        = Exit")
        print()
        print("Move the mouse and press/release the inputs.")
        print()

        self._print_state(force=True)

    # ==========================================================
    # EVENTS
    # ==========================================================

    def handle_event(self, event):
        if event.type == sdl3.SDL_EVENT_KEY_DOWN:
            scancode = int(event.key.scancode)

            if scancode == sdl3.SDL_SCANCODE_ESCAPE:
                self.stop()

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(self, delta_time):
        self._print_state()

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(self):
        # Input test does not require rendering.
        pass

    # ==========================================================
    # OUTPUT
    # ==========================================================

    def _print_state(self, force=False):
        left_down = self.input.action_down("left")
        left_pressed = self.input.action_pressed("left")
        left_released = self.input.action_released("left")

        right_down = self.input.action_down("right")
        right_pressed = self.input.action_pressed("right")
        right_released = self.input.action_released("right")

        jump_down = self.input.action_down("jump")
        jump_pressed = self.input.action_pressed("jump")
        jump_released = self.input.action_released("jump")

        fire_down = self.input.action_down("fire")
        fire_pressed = self.input.action_pressed("fire")
        fire_released = self.input.action_released("fire")

        mouse_x, mouse_y = self.input.mouse_position
        mouse_dx, mouse_dy = self.input.mouse_delta
        wheel_x, wheel_y = self.input.wheel

        state = (
            left_down,
            left_pressed,
            left_released,
            right_down,
            right_pressed,
            right_released,
            jump_down,
            jump_pressed,
            jump_released,
            fire_down,
            fire_pressed,
            fire_released,
            mouse_x,
            mouse_y,
            mouse_dx,
            mouse_dy,
            wheel_x,
            wheel_y,
            self.input.focused,
        )

        # Avoid flooding the console when nothing changed.
        if not force and state == self._last_output:
            return

        self._last_output = state

        print(
            "\033[2J\033[H",
            end="",
        )

        print("=" * 50)
        print(" Nexora Input System Test")
        print("=" * 50)
        print()

        print("Keyboard")
        print("-" * 50)

        self._print_action(
            "A / left",
            left_down,
            left_pressed,
            left_released,
        )

        self._print_action(
            "D / right",
            right_down,
            right_pressed,
            right_released,
        )

        self._print_action(
            "SPACE / jump",
            jump_down,
            jump_pressed,
            jump_released,
        )

        print()

        print("Mouse")
        print("-" * 50)

        print(
            f"Position: {mouse_x:7.1f}, {mouse_y:7.1f}"
        )

        print(
            f"Delta:    {mouse_dx:7.1f}, {mouse_dy:7.1f}"
        )

        print(
            f"Wheel:    {wheel_x:7.1f}, {wheel_y:7.1f}"
        )

        self._print_action(
            "Left Mouse / fire",
            fire_down,
            fire_pressed,
            fire_released,
        )

        print()

        print("Input State")
        print("-" * 50)

        print(
            f"Focused:      {self.input.focused}"
        )

        print(
            f"Keys down:    {len(self.input.keys_down)}"
        )

        print(
            f"Mouse down:   "
            f"{len(self.input.mouse_buttons_down)}"
        )

        print()

        print("Direct API")
        print("-" * 50)

        print(
            f"key_down('A'):      "
            f"{self.input.key_down('A')}"
        )

        print(
            f"key_pressed('A'):   "
            f"{self.input.key_pressed('A')}"
        )

        print(
            f"key_released('A'):  "
            f"{self.input.key_released('A')}"
        )

        print()

        print("Actions")
        print("-" * 50)

        print(
            f"left:   "
            f"{self._action_status('left')}"
        )

        print(
            f"right:  "
            f"{self._action_status('right')}"
        )

        print(
            f"jump:   "
            f"{self._action_status('jump')}"
        )

        print(
            f"fire:   "
            f"{self._action_status('fire')}"
        )

        print()

        print("Press ESC to exit.")

    @staticmethod
    def _print_action(
        name,
        down,
        pressed,
        released,
    ):
        print(name)

        print(
            f"  Down:     {down}"
        )

        print(
            f"  Pressed:  {pressed}"
        )

        print(
            f"  Released: {released}"
        )

    def _action_status(self, action):
        state = self.input.action(action)

        if state.pressed:
            return "PRESSED"

        if state.released:
            return "RELEASED"

        if state.down:
            return "DOWN"

        return "UP"


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    game = InputTestGame()

    try:
        game.run()

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")

    finally:
        print()
        print("=" * 50)
        print(" Input system test finished.")
        print("=" * 50)