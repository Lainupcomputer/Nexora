from nexora import Game
from nexora.scene import Scene


class MainScene(Scene):
    def __init__(
        self,
        game,
    ) -> None:
        super().__init__(
            "Main"
        )

        self.game = game

    def update(
        self,
        delta_time: float,
    ) -> None:
        super().update(
            delta_time
        )

        if self.game.input.action_pressed.pause:
            self.game.stop()

    def render(
        self,
        interpolation: float,
    ) -> None:
        self.game.renderer.rect(
            -50.0,
            -50.0,
            100.0,
            100.0,
        )


class MyGame(Game):
    def initialize(
        self,
    ) -> None:
        self.scene = MainScene(
            self
        )


if __name__ == "__main__":
    MyGame().run()