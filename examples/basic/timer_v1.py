from __future__ import annotations

from nexora.core.game import Game
from nexora.scene import Scene


class TimerExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="TimerExample",
            title="Nexora - Timer System V1",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )
        self.tick_count = 0
        self.repeating_timer = None

    def initialize(self) -> None:
        self.scene = Scene("TimerExample")

        self.input.bind("exit", "ESCAPE")
        self.input.bind("schedule", "SPACE")
        self.input.bind("toggle_timer_pause", "P")

        print("=" * 60)
        print(" Nexora Timer System V1")
        print("=" * 60)
        print("SPACE -> call_later(2s)")
        print("P     -> pause/resume repeating timer")
        print("ESC   -> exit")
        print()

        self.repeating_timer = self.timers.call_every(
            1.0,
            self._tick,
            repeat=-1,
        )

    def _tick(self) -> None:
        self.tick_count += 1
        print(f"[Timer] repeating tick #{self.tick_count}")

    def _delayed_message(self) -> None:
        print("[Timer] delayed callback fired after 2 seconds")
        self.notifications.info(
            "Delayed callback fired.",
            title="Timer",
            duration=2.5,
        )

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return

        if self.input.action("schedule").pressed:
            print("[Timer] scheduled callback for +2.0s")
            self.timers.call_later(
                2.0,
                self._delayed_message,
            )

        if self.input.action(
            "toggle_timer_pause"
        ).pressed:
            if self.timers.paused:
                self.timers.resume()

                print(
                    "[Timer] TimerManager resumed"
                )

                self.notifications.success(
                    "TimerManager resumed.",
                    title="Timer",
                    duration=2.0,
                )

            else:
                self.timers.pause()

                print(
                    "[Timer] TimerManager paused"
                )

                self.notifications.warning(
                    "TimerManager paused.",
                    title="Timer",
                    duration=2.0,
                )
        super().update(delta_time)


if __name__ == "__main__":
    TimerExample().run()
