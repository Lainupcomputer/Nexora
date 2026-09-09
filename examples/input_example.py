from __future__ import annotations

from nexora.core.engine import Engine


class InputExample:
    def __init__(self):
        self.engine = None
        self.input = None
        self.window = None
        self.renderer = None

        self.x = 640.0
        self.y = 360.0

        self.size = 64
        self.speed = 350.0

        self.click_timer = 0.0

    def initialize(self):
        self.input.bind("move_up", "W")
        self.input.bind("move_up", "UP")

        self.input.bind("move_down", "S")
        self.input.bind("move_down", "DOWN")

        self.input.bind("move_left", "A")
        self.input.bind("move_left", "LEFT")

        self.input.bind("move_right", "D")
        self.input.bind("move_right", "RIGHT")

        self.input.bind("quit", "ESCAPE")
        self.input.bind("action", "MOUSE_LEFT")

        self.renderer.clear_color = (
            25,
            25,
            30,
        )

    def handle_event(self, event):
        pass

    def fixed_update(self, fixed_delta_time):
        pass

    def update(self, delta_time):
        # --------------------------------------------------------------
        # Quit
        # --------------------------------------------------------------

        if self.input.is_pressed("quit"):
            self.engine.stop()
            return

        # --------------------------------------------------------------
        # Movement
        # --------------------------------------------------------------

        direction_x = 0.0
        direction_y = 0.0

        if self.input.is_down("move_left"):
            direction_x -= 1.0

        if self.input.is_down("move_right"):
            direction_x += 1.0

        if self.input.is_down("move_up"):
            direction_y -= 1.0

        if self.input.is_down("move_down"):
            direction_y += 1.0

        # Normalize diagonal movement.
        if direction_x != 0.0 or direction_y != 0.0:
            length = (
                direction_x * direction_x
                + direction_y * direction_y
            ) ** 0.5

            direction_x /= length
            direction_y /= length

        self.x += direction_x * self.speed * delta_time
        self.y += direction_y * self.speed * delta_time

        # --------------------------------------------------------------
        # Keep player inside window
        # --------------------------------------------------------------

        half_size = self.size / 2

        self.x = max(
            half_size,
            min(
                self.window.width - half_size,
                self.x,
            ),
        )

        self.y = max(
            half_size,
            min(
                self.window.height - half_size,
                self.y,
            ),
        )

        # --------------------------------------------------------------
        # Mouse action
        # --------------------------------------------------------------

        if self.input.is_pressed("action"):
            self.click_timer = 0.15

        if self.click_timer > 0.0:
            self.click_timer -= delta_time

    def render(self):
        # --------------------------------------------------------------
        # Player
        # --------------------------------------------------------------

        player_color = (
            255,
            80,
            80,
        )

        if self.click_timer > 0.0:
            player_color = (
                255,
                220,
                80,
            )

        self.renderer.rectangle(
            self.x - self.size / 2,
            self.y - self.size / 2,
            self.size,
            self.size,
            color=player_color,
        )

        # --------------------------------------------------------------
        # Mouse
        # --------------------------------------------------------------

        mouse_x, mouse_y = self.input.mouse_position()

        self.renderer.circle(
            mouse_x,
            mouse_y,
            6,
            color=(
                100,
                180,
                255,
            ),
        )

        # --------------------------------------------------------------
        # UI
        # --------------------------------------------------------------

        self.renderer.text(
            "WASD / Arrow Keys = Move    ESC = Quit",
            20,
            20,
            size=28,
            color=(
                230,
                230,
                230,
            ),
        )

        self.renderer.text(
            f"Mouse: {mouse_x}, {mouse_y}",
            20,
            50,
            size=28,
            color=(
                180,
                180,
                180,
            ),
        )

    def shutdown(self):
        pass


def main():
    game = InputExample()

    engine = Engine(
        game,
        width=1280,
        height=720,
        title="Nexora Engine - Input + Renderer",
        target_fps=144,
        fixed_delta_time=1.0 / 60.0,
        resizable=True,
    )

    engine.run()


if __name__ == "__main__":
    main()