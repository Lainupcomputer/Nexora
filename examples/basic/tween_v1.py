from __future__ import annotations

from dataclasses import dataclass

from nexora.core.game import Game
from nexora.scene import Scene


@dataclass
class DemoState:
    x: float = -420.0
    y: float = 0.0
    size: float = 48.0
    color: tuple[float, float, float, float] = (1.0, 0.25, 0.4, 1.0)


class TweenExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="TweenExample",
            title="Nexora - Tween V1",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )
        self.demo = DemoState()
        self.sequence = None

    def initialize(self) -> None:
        self.scene = Scene("TweenExample")
        self.input.bind("exit", "ESCAPE")
        self.input.bind("restart_tween", "SPACE")
        self.input.bind("pause_tweens", "P")

        self._start_sequence()

        print("=" * 60)
        print(" Nexora Tween V1")
        print("=" * 60)
        print("SPACE -> Restart sequence")
        print("P     -> Pause/resume tween manager")
        print("ESC   -> Exit")

    def _start_sequence(self) -> None:
        if self.sequence is not None and self.sequence.active:
            self.sequence.stop()

        self.demo.x = -420.0
        self.demo.y = 0.0
        self.demo.size = 48.0
        self.demo.color = (1.0, 0.25, 0.4, 1.0)

        sequence = self.tweens.sequence()
        sequence.to(
            self.demo,
            "x",
            420.0,
            duration=1.5,
            easing="back_out",
        )
        sequence.to(
            self.demo,
            "size",
            110.0,
            duration=0.45,
            easing="sine_out",
        )
        sequence.to(
            self.demo,
            "color",
            (0.2, 0.65, 1.0, 1.0),
            duration=0.7,
            easing="sine_in_out",
        )
        sequence.wait(0.35)
        sequence.to(
            self.demo,
            "x",
            -420.0,
            duration=1.3,
            easing="bounce_out",
        )
        sequence.to(
            self.demo,
            "size",
            48.0,
            duration=0.35,
            easing="quad_out",
        )
        sequence.call(lambda: print("Tween sequence finished."))

        self.sequence = sequence

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return

        if self.input.action("restart_tween").pressed:
            self._start_sequence()

        if self.input.action("pause_tweens").pressed:
            if getattr(self, "_tweens_paused", False):
                self.tweens.resume()
                self._tweens_paused = False
                print("Tweens: RESUMED")
            else:
                self.tweens.pause()
                self._tweens_paused = True
                print("Tweens: PAUSED")

        super().update(delta_time)

    def render(self, interpolation: float) -> None:
        self.renderer.rect(
            self.demo.x,
            self.demo.y,
            self.demo.size,
            self.demo.size,
            color=self.demo.color,
            radius=14.0,
            layer=0,
        )

        # Reference line through the center.
        self.renderer.line(
            -500.0,
            0.0,
            500.0,
            0.0,
            width=2.0,
            color=(0.35, 0.35, 0.4, 1.0),
            layer=-1,
        )

        super().render(interpolation)


if __name__ == "__main__":
    TweenExample().run()
