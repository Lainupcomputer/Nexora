from __future__ import annotations

from nexora import Game


class GameLoopMemoryTest(Game):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - GameLoop Memory Test",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

    def initialize(
        self,
    ) -> None:
        self.input.bind(
            "escape",
            "ESCAPE",
        )

        self.renderer.post_processing.enabled = False

        print()
        print("=" * 70)
        print(" Nexora GameLoop Memory Test")
        print("=" * 70)
        print()
        print("Target FPS:              144")
        print("Post processing:         OFF")
        print("Game update:             EMPTY")
        print("Game fixed update:       EMPTY")
        print("Game render:             EMPTY")
        print("AudioPlayer.update():    ENABLED")
        print()
        print("NO super().update()")
        print("NO super().render()")
        print()
        print("ESC Exit")
        print()

    def update(
        self,
        delta_time: float,
    ) -> None:
        if self.input.action(
            "escape"
        ).pressed:
            self.stop()

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:
        pass

    def render(
        self,
        interpolation: float,
    ) -> None:
        pass


if __name__ == "__main__":
    GameLoopMemoryTest().run()