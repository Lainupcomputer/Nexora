from __future__ import annotations

import math

from nexora.ecs.world import World
from nexora.nodes.node import Node
from nexora.tween import EASINGS, TweenManager


class Target:
    def __init__(self) -> None:
        self.value = 0.0
        self.color = (0.0, 0.0, 0.0, 1.0)


class Nested:
    def __init__(self) -> None:
        self.inner = Target()


def test_easings_have_valid_endpoints():
    for name, easing in EASINGS.items():
        assert math.isclose(easing(0.0), 0.0, abs_tol=1e-6), name
        assert math.isclose(easing(1.0), 1.0, abs_tol=1e-6), name


def test_manager_tweens_float_property():
    target = Target()
    manager = TweenManager()

    manager.to(target, "value", 10.0, duration=1.0)
    manager.update(0.5, 0.5)

    assert math.isclose(target.value, 5.0)
    assert manager.active_count == 1

    manager.update(0.5, 0.5)

    assert math.isclose(target.value, 10.0)
    assert manager.active_count == 0


def test_dotted_property_path():
    target = Nested()
    manager = TweenManager()

    manager.to(target, "inner.value", 8.0, duration=1.0)
    manager.update(0.25, 0.25)

    assert math.isclose(target.inner.value, 2.0)


def test_tuple_interpolation_supports_colors():
    target = Target()
    manager = TweenManager()

    manager.to(
        target,
        "color",
        (1.0, 0.5, 0.25, 0.0),
        duration=1.0,
    )
    manager.update(0.5, 0.5)

    assert target.color == (0.5, 0.25, 0.125, 0.5)


def test_delay_waits_before_starting():
    target = Target()
    manager = TweenManager()

    tween = manager.to(
        target,
        "value",
        10.0,
        duration=1.0,
        delay=0.5,
    )

    started = []
    tween.started.connect(lambda _tween: started.append(True))

    manager.update(0.25, 0.25)
    assert target.value == 0.0
    assert started == []

    manager.update(0.25, 0.25)
    assert started == [True]
    assert target.value == 0.0

    manager.update(0.5, 0.5)
    assert math.isclose(target.value, 5.0)


def test_yoyo_returns_to_start():
    target = Target()
    manager = TweenManager()

    manager.to(
        target,
        "value",
        10.0,
        duration=1.0,
        loops=1,
        yoyo=True,
    )

    manager.update(1.0, 1.0)
    assert math.isclose(target.value, 10.0)

    manager.update(1.0, 1.0)
    assert math.isclose(target.value, 0.0)
    assert manager.active_count == 0


def test_pause_and_resume():
    target = Target()
    manager = TweenManager()
    tween = manager.to(target, "value", 10.0, duration=1.0)

    tween.pause()
    manager.update(0.5, 0.5)
    assert target.value == 0.0

    tween.resume()
    manager.update(0.5, 0.5)
    assert math.isclose(target.value, 5.0)


def test_ignore_time_scale_uses_unscaled_delta():
    target = Target()
    manager = TweenManager()

    manager.to(
        target,
        "value",
        10.0,
        duration=1.0,
        ignore_time_scale=True,
    )

    manager.update(0.0, 0.5)
    assert math.isclose(target.value, 5.0)


def test_from_to_sets_start_immediately():
    target = Target()
    target.value = 50.0
    manager = TweenManager()

    manager.from_to(
        target,
        "value",
        -10.0,
        10.0,
        duration=1.0,
    )

    assert target.value == -10.0
    manager.update(0.5, 0.5)
    assert math.isclose(target.value, 0.0)


def test_node_destroy_stops_owned_tween_immediately():
    world = World()
    node = Node("TweenOwner", world)
    manager = TweenManager()

    tween = manager.to(
        node,
        "transform.x",
        100.0,
        duration=1.0,
    )

    assert tween.active
    assert tween in node._owned_tweens

    node.destroy()

    assert not tween.active
    assert tween not in node._owned_tweens


def test_manager_kill_owner():
    owner = Target()
    manager = TweenManager()
    first = manager.to(owner, "value", 10.0, duration=1.0)
    second_target = Target()
    second = manager.to(second_target, "value", 10.0, duration=1.0)

    assert manager.kill_owner(owner) == 1
    assert not first.active
    assert second.active


def test_sequence_runs_tweens_wait_and_callback_in_order():
    target = Target()
    manager = TweenManager()
    calls = []

    sequence = manager.sequence()
    sequence.to(target, "value", 10.0, duration=1.0)
    sequence.wait(0.5)
    sequence.call(lambda: calls.append("done"))
    sequence.to(target, "value", 20.0, duration=1.0)

    manager.update(1.0, 1.0)
    assert math.isclose(target.value, 10.0)

    manager.update(0.25, 0.25)
    assert calls == []

    manager.update(0.25, 0.25)
    # Wait completes here; callback is allowed to run in the same tick.
    assert calls == ["done"]

    manager.update(0.5, 0.5)
    assert math.isclose(target.value, 15.0)

    manager.update(0.5, 0.5)
    assert math.isclose(target.value, 20.0)
    assert not sequence.active


def test_tween_signals_fire():
    target = Target()
    manager = TweenManager()
    tween = manager.to(target, "value", 1.0, duration=0.5)

    calls = []
    tween.started.connect(lambda _t: calls.append("started"))
    tween.step.connect(lambda _t, _p, _v: calls.append("step"))
    tween.finished.connect(lambda _t: calls.append("finished"))

    manager.update(0.5, 0.5)

    assert calls[0] == "started"
    assert "step" in calls
    assert calls[-1] == "finished"
