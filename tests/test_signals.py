from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes.node import Node
from nexora.signals import (
    EventBus,
    Signal,
)


def test_signal_emits_arguments():
    signal = Signal("changed")
    received = []

    signal.connect(
        lambda value, name=None: received.append(
            (value, name)
        )
    )

    signal.emit(
        42,
        name="player",
    )

    assert received == [
        (42, "player")
    ]


def test_signal_disconnect_by_connection():
    signal = Signal("changed")
    received = []

    connection = signal.connect(
        received.append
    )

    signal.emit(1)
    connection.disconnect()
    signal.emit(2)

    assert received == [1]
    assert not connection.connected


def test_signal_disconnect_by_bound_method():
    signal = Signal("changed")

    class Receiver:
        def __init__(self):
            self.values = []

        def on_changed(self, value):
            self.values.append(value)

    receiver = Receiver()

    signal.connect(
        receiver.on_changed
    )

    assert signal.is_connected(
        receiver.on_changed
    )

    assert signal.disconnect(
        receiver.on_changed
    )

    signal.emit(5)

    assert receiver.values == []


def test_once_connection_runs_once():
    signal = Signal("ready")
    calls = []

    signal.connect(
        lambda: calls.append(True),
        once=True,
    )

    signal.emit()
    signal.emit()

    assert calls == [True]
    assert len(signal) == 0


def test_signal_priority_is_stable():
    signal = Signal("ordered")
    calls = []

    signal.connect(
        lambda: calls.append("normal-a"),
    )
    signal.connect(
        lambda: calls.append("high"),
        priority=10,
    )
    signal.connect(
        lambda: calls.append("normal-b"),
    )

    signal.emit()

    assert calls == [
        "high",
        "normal-a",
        "normal-b",
    ]


def test_connection_can_be_blocked():
    signal = Signal("changed")
    calls = []

    connection = signal.connect(
        calls.append
    )

    connection.block()
    signal.emit(1)

    connection.unblock()
    signal.emit(2)

    assert calls == [2]


def test_node_create_signal_is_cleared_on_destroy():
    world = World()
    source = Node("Source", world)

    changed = source.create_signal(
        "changed"
    )

    calls = []
    changed.connect(
        calls.append
    )

    source.destroy()

    changed.emit(1)

    assert calls == []
    assert len(changed) == 0


def test_bound_node_listener_disconnects_on_destroy():
    world = World()
    source = Node("Source", world)
    listener = Node("Listener", world)

    source.changed = source.create_signal(
        "changed"
    )

    calls = []

    def callback(value):
        calls.append(value)

    # Explicit owner supports lambdas/free functions too.
    source.changed.connect(
        callback,
        owner=listener,
    )

    source.changed.emit(1)
    listener.destroy()
    source.changed.emit(2)

    assert calls == [1]
    assert len(source.changed) == 0


def test_bound_node_method_owner_is_inferred():
    world = World()

    class ReceiverNode(Node):
        def __init__(self, name, world):
            super().__init__(name, world)
            self.values = []

        def receive(self, value):
            self.values.append(value)

    source = Node("Source", world)
    listener = ReceiverNode(
        "Listener",
        world,
    )

    changed = source.create_signal(
        "changed"
    )

    changed.connect(
        listener.receive
    )

    changed.emit(1)
    listener.destroy()
    changed.emit(2)

    assert listener.values == [1]
    assert len(changed) == 0


def test_event_bus_reuses_named_signal():
    bus = EventBus()

    assert (
        bus.signal("player.died")
        is bus.signal("player.died")
    )


def test_event_bus_connect_emit_and_clear():
    bus = EventBus()
    calls = []

    bus.connect(
        "game.saved",
        calls.append,
    )

    bus.emit(
        "game.saved",
        "slot_1",
    )

    assert calls == ["slot_1"]

    bus.clear(
        "game.saved"
    )

    bus.emit(
        "game.saved",
        "slot_2",
    )

    assert calls == ["slot_1"]
