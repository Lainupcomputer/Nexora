from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes.node import Node
from nexora.timer import TimerManager


def test_call_later_fires_once():
    manager = TimerManager()
    calls = []

    manager.call_later(0.5, lambda: calls.append("done"))
    manager.update(0.25, 0.25)
    assert calls == []
    assert manager.active_count == 1

    manager.update(0.25, 0.25)
    assert calls == ["done"]
    assert manager.active_count == 0


def test_call_every_repeat_counts_additional_timeouts():
    manager = TimerManager()
    calls = []

    manager.call_every(
        0.25,
        lambda: calls.append(len(calls) + 1),
        repeat=2,
    )

    manager.update(0.25, 0.25)
    manager.update(0.25, 0.25)
    manager.update(0.25, 0.25)

    assert calls == [1, 2, 3]
    assert manager.active_count == 0


def test_large_delta_preserves_interval_remainder():
    manager = TimerManager()
    calls = []

    timer = manager.call_every(
        0.25,
        lambda: calls.append(True),
        repeat=4,
    )

    manager.update(0.6, 0.6)

    assert len(calls) == 2
    assert abs(timer.elapsed - 0.1) < 1e-9


def test_infinite_repeating_timer_can_be_cancelled():
    manager = TimerManager()
    calls = []

    timer = manager.call_every(
        0.1,
        lambda: calls.append(True),
    )

    manager.update(0.3, 0.3)
    assert len(calls) == 2 or len(calls) == 3

    # Floating point boundaries may leave the exact third timeout for the
    # following tick. Cancellation semantics are what this test targets.
    timer.cancel()
    manager.update(1.0, 1.0)
    before = len(calls)
    manager.update(1.0, 1.0)
    assert len(calls) == before
    assert manager.active_count == 0


def test_pause_and_resume():
    manager = TimerManager()
    calls = []
    timer = manager.call_later(1.0, lambda: calls.append(True))

    timer.pause()
    manager.update(1.0, 1.0)
    assert calls == []

    timer.resume()
    manager.update(1.0, 1.0)
    assert calls == [True]


def test_manager_pause_and_resume():
    manager = TimerManager()
    calls = []
    manager.call_later(0.5, lambda: calls.append(True))

    manager.pause()
    manager.update(1.0, 1.0)
    assert calls == []

    manager.resume()
    manager.update(0.5, 0.5)
    assert calls == [True]


def test_ignore_time_scale_uses_unscaled_delta():
    manager = TimerManager()
    calls = []

    manager.call_later(
        0.5,
        lambda: calls.append(True),
        ignore_time_scale=True,
    )

    manager.update(0.0, 0.5)
    assert calls == [True]


def test_immediate_repeating_timer_fires_on_first_update():
    manager = TimerManager()
    calls = []

    manager.call_every(
        1.0,
        lambda: calls.append(True),
        repeat=1,
        immediate=True,
    )

    manager.update(0.0, 0.0)
    assert len(calls) == 1
    assert manager.active_count == 1

    manager.update(1.0, 1.0)
    assert len(calls) == 2
    assert manager.active_count == 0


def test_timer_signals_fire():
    manager = TimerManager()
    timer = manager.create(0.5)
    events = []

    timer.started.connect(lambda _timer: events.append("started"))
    timer.timeout.connect(
        lambda _timer, count: events.append(("timeout", count))
    )
    timer.finished.connect(lambda _timer: events.append("finished"))

    manager.update(0.5, 0.5)

    assert events == [
        "started",
        ("timeout", 1),
        "finished",
    ]


def test_node_destroy_cancels_owned_timer_immediately():
    world = World()
    node = Node("TimerOwner", world)
    manager = TimerManager()
    calls = []

    timer = manager.call_later(
        1.0,
        lambda: calls.append(True),
        owner=node,
    )

    assert timer in node._owned_timers
    assert timer.active

    node.destroy()

    assert not timer.active
    assert timer not in node._owned_timers

    manager.update(2.0, 2.0)
    assert calls == []


def test_manager_kill_owner_only_cancels_matching_timers():
    first_owner = object()
    second_owner = object()
    manager = TimerManager()

    first = manager.call_later(1.0, lambda: None, owner=first_owner)
    second = manager.call_later(1.0, lambda: None, owner=second_owner)

    assert manager.kill_owner(first_owner) == 1
    assert not first.active
    assert second.active


def test_zero_duration_timer_does_not_loop_forever():
    manager = TimerManager()
    calls = []

    timer = manager.call_every(
        0.0,
        lambda: calls.append(True),
        repeat=-1,
    )

    manager.update(1.0, 1.0)
    assert calls == [True]
    assert timer.active
