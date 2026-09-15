from __future__ import annotations

from nexora.core.game import Game
from nexora.scene import Scene
from nexora.signals import Signal
from nexora.tasks import (
    call,
    wait,
    wait_signal,
    wait_timer,
    wait_tween,
)


class DemoValue:
    def __init__(self) -> None:
        self.value = 0.0


class TaskExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="TaskExample",
            title="Nexora - Coroutine Tasks V1",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )

        self.demo = DemoValue()
        self.continue_signal = Signal(
            "task_example.continue"
        )
        self.demo_task = None

    def initialize(self) -> None:
        self.scene = Scene("TaskExample")

        self.input.bind("exit", "ESCAPE")
        self.input.bind("continue_demo", "SPACE")
        self.input.bind("toggle_tasks", "P")

        print("=" * 60)
        print(" Nexora Coroutine / Task System V1")
        print("=" * 60)
        print("SPACE -> emit signal when the coroutine asks for it")
        print("P     -> pause/resume TaskManager")
        print("ESC   -> exit")
        print()

        self.demo_task = self.tasks.start(
            self._demo_routine,
            name="task-demo",
        )

        self.demo_task.finished.connect(
            self._on_demo_finished
        )

    def _demo_routine(self):
        print("[Task] started")
        print("[Task] waiting 1 second...")
        yield wait(1.0)

        print("[Task] starting tween 0 -> 100")
        tween = self.tweens.to(
            self.demo,
            "value",
            100.0,
            duration=1.0,
            easing="sine_in_out",
        )
        yield wait_tween(tween)
        print(
            f"[Task] tween done, value={self.demo.value:.1f}"
        )

        print("[Task] starting 1 second timer")
        timer = self.timers.call_later(
            1.0,
            lambda: print("[Timer] timeout"),
        )
        yield wait_timer(timer)

        result = yield call(
            lambda a, b: a + b,
            20,
            22,
        )
        print(f"[Task] call() returned {result}")

        print("[Task] press SPACE to continue...")
        payload = yield wait_signal(
            self.continue_signal
        )
        print(f"[Task] signal payload: {payload!r}")

        return "demo complete"

    def _on_demo_finished(
        self,
        task,
        result,
    ) -> None:
        print(f"[Task] finished: {result}")

        self.notifications.success(
            "Coroutine demo finished.",
            title="Tasks",
            duration=3.0,
        )

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return

        if self.input.action("continue_demo").pressed:
            self.continue_signal.emit(
                "SPACE"
            )

        if self.input.action("toggle_tasks").pressed:
            if self.tasks.paused:
                self.tasks.resume()
                print("[Task] TaskManager resumed")
            else:
                self.tasks.pause()
                print("[Task] TaskManager paused")

        super().update(delta_time)


if __name__ == "__main__":
    TaskExample().run()
