from __future__ import annotations

import math

import pytest

from nexora.signals import Signal
from nexora.tasks import (
    TaskManager,
    call,
    next_frame,
    wait,
    wait_frames,
    wait_signal,
    wait_task,
    wait_timer,
    wait_tween,
    wait_until,
)


class ActiveObject:
    def __init__(self) -> None:
        self.active = True


class FakeWorld:
    def __init__(self) -> None:
        self.alive = True

    def is_alive(self, entity) -> bool:
        return self.alive


class Owner:
    def __init__(self) -> None:
        self.world = FakeWorld()
        self.entity = 1
        self.tasks = set()

    def _track_task(self, task) -> None:
        self.tasks.add(task)

    def _untrack_task(self, task) -> None:
        self.tasks.discard(task)


def test_task_wait_seconds_and_result():
    manager = TaskManager()
    values = []

    def routine():
        values.append("start")
        yield wait(1.0)
        values.append("done")
        return 42

    task = manager.start(routine)

    manager.update(0.0, 0.0)
    assert values == ["start"]
    assert task.active

    manager.update(0.5, 0.5)
    assert values == ["start"]

    manager.update(0.5, 0.5)
    assert values == ["start", "done"]
    assert not task.active
    assert task.result == 42


def test_wait_frames_and_none_mean_next_frame():
    manager = TaskManager()
    values = []

    def routine():
        values.append(0)
        yield wait_frames(2)
        values.append(1)
        yield None
        values.append(2)

    manager.start(routine)
    manager.update(0.1, 0.1)
    assert values == [0]
    manager.update(0.1, 0.1)
    assert values == [0]
    manager.update(0.1, 0.1)
    assert values == [0, 1]
    manager.update(0.1, 0.1)
    assert values == [0, 1, 2]


def test_next_frame_alias():
    manager = TaskManager()
    values = []

    def routine():
        values.append("a")
        yield next_frame()
        values.append("b")

    manager.start(routine)
    manager.update(0.0, 0.0)
    assert values == ["a"]
    manager.update(0.0, 0.0)
    assert values == ["a", "b"]


def test_wait_until_returns_predicate_value():
    manager = TaskManager()
    state = {"ready": False}
    received = []

    def routine():
        value = yield wait_until(
            lambda: "ready" if state["ready"] else ""
        )
        received.append(value)

    manager.start(routine)
    manager.update(0.0, 0.0)
    manager.update(0.0, 0.0)
    assert received == []

    state["ready"] = True
    manager.update(0.0, 0.0)
    assert received == ["ready"]


def test_wait_signal_sends_emitted_value_back():
    manager = TaskManager()
    signal = Signal("test")
    received = []

    def routine():
        value = yield wait_signal(signal)
        received.append(value)

    manager.start(routine)
    manager.update(0.0, 0.0)
    signal.emit(123)
    manager.update(0.0, 0.0)

    assert received == [123]


def test_wait_signal_multiple_args_returns_tuple():
    manager = TaskManager()
    signal = Signal("test")
    received = []

    def routine():
        value = yield wait_signal(signal)
        received.append(value)

    manager.start(routine)
    manager.update(0.0, 0.0)
    signal.emit(1, 2)
    manager.update(0.0, 0.0)

    assert received == [(1, 2)]


def test_call_runs_immediately_inside_task():
    manager = TaskManager()
    values = []

    def routine():
        result = yield call(lambda a, b: a + b, 2, 3)
        values.append(result)
        yield next_frame()

    manager.start(routine)
    manager.update(0.0, 0.0)
    assert values == [5]


def test_wait_runtime_objects():
    manager = TaskManager()
    tween = ActiveObject()
    timer = ActiveObject()
    child_obj = ActiveObject()
    values = []

    def routine():
        assert (yield wait_tween(tween)) is tween
        values.append("tween")
        assert (yield wait_timer(timer)) is timer
        values.append("timer")
        assert (yield wait_task(child_obj)) is child_obj
        values.append("task")

    manager.start(routine)
    manager.update(0.0, 0.0)

    tween.active = False
    manager.update(0.0, 0.0)
    assert values == ["tween"]

    timer.active = False
    manager.update(0.0, 0.0)
    assert values == ["tween", "timer"]

    child_obj.active = False
    manager.update(0.0, 0.0)
    assert values == ["tween", "timer", "task"]


def test_task_pause_resume():
    manager = TaskManager()
    values = []

    def routine():
        yield wait(1.0)
        values.append("done")

    task = manager.start(routine)
    manager.update(0.0, 0.0)
    manager.update(0.5, 0.5)
    task.pause()
    manager.update(1.0, 1.0)
    assert values == []

    task.resume()
    manager.update(0.5, 0.5)
    assert values == ["done"]


def test_manager_pause_resume():
    manager = TaskManager()
    values = []

    def routine():
        yield wait(1.0)
        values.append("done")

    manager.start(routine)
    manager.update(0.0, 0.0)
    manager.pause()
    manager.update(2.0, 2.0)
    assert values == []
    manager.resume()
    manager.update(1.0, 1.0)
    assert values == ["done"]


def test_unscaled_wait_inherits_task_setting():
    manager = TaskManager()
    values = []

    def routine():
        yield wait(1.0)
        values.append("done")

    manager.start(
        routine,
        ignore_time_scale=True,
    )
    manager.update(0.0, 0.0)
    manager.update(0.0, 0.5)
    assert values == []
    manager.update(0.0, 0.5)
    assert values == ["done"]


def test_wait_can_override_task_time_mode():
    manager = TaskManager()
    values = []

    def routine():
        yield wait(
            1.0,
            ignore_time_scale=False,
        )
        values.append("done")

    manager.start(
        routine,
        ignore_time_scale=True,
    )
    manager.update(0.0, 0.0)
    manager.update(0.5, 1.0)
    assert values == []
    manager.update(0.5, 1.0)
    assert values == ["done"]


def test_owner_is_tracked_and_dead_owner_cancels_task():
    manager = TaskManager()
    owner = Owner()

    def routine():
        yield wait(10.0)

    task = manager.start(
        routine,
        owner=owner,
    )
    assert task in owner.tasks

    manager.update(0.0, 0.0)
    owner.world.alive = False
    manager.update(0.1, 0.1)

    assert not task.active
    assert task not in owner.tasks


def test_kill_owner():
    manager = TaskManager()
    owner = Owner()

    def routine():
        yield wait(10.0)

    first = manager.start(routine, owner=owner)
    second = manager.start(routine, owner=owner)

    assert manager.kill_owner(owner) == 2
    assert not first.active
    assert not second.active
    assert manager.active_count == 0


def test_task_signals():
    manager = TaskManager()
    events = []

    def routine():
        yield next_frame()
        return "ok"

    task = manager.start(routine)
    task.started.connect(lambda task: events.append("started"))
    task.yielded.connect(lambda task, value: events.append("yielded"))
    task.finished.connect(
        lambda task, result: events.append(("finished", result))
    )

    manager.update(0.0, 0.0)
    manager.update(0.0, 0.0)

    assert events == [
        "started",
        "yielded",
        ("finished", "ok"),
    ]


def test_task_failure_is_recorded_and_reraised():
    manager = TaskManager()

    def routine():
        yield next_frame()
        raise RuntimeError("boom")

    task = manager.start(routine)
    manager.update(0.0, 0.0)

    with pytest.raises(RuntimeError, match="boom"):
        manager.update(0.0, 0.0)

    assert not task.active
    assert isinstance(task.exception, RuntimeError)
