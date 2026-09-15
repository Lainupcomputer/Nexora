from __future__ import annotations

from nexora.animation import (
    AnimationClip,
    AnimationEvent,
    AnimationFrame,
    AnimationPlayer,
    AnimationStateMachine,
    Animator,
)
from nexora.ecs.world import World
from nexora.nodes import AnimatedSprite, Node
from nexora.scene.serialization.registry import NodeFactoryRegistry


def clip(name="attack", *, loop=False):
    return AnimationClip(
        name=name,
        frames=(
            AnimationFrame(0, 0.1),
            AnimationFrame(1, 0.1),
            AnimationFrame(2, 0.1),
        ),
        loop=loop,
        events=(AnimationEvent(1, "hit", {"damage": 5}),),
    )


def test_animation_event_validates_frame_range():
    try:
        AnimationClip(
            "bad",
            (AnimationFrame(0, 0.1),),
            events=(AnimationEvent(1, "bad"),),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_clip_with_event_returns_copy():
    base = AnimationClip("idle", (AnimationFrame(0, 0.1),))
    changed = base.with_event(0, "blink")
    assert base.events == ()
    assert changed.events[0].name == "blink"


def test_animator_emits_frame_event():
    animator = Animator()
    animator.add_clip(clip())
    received = []
    animator.on_event = received.append
    animator.play("attack")
    animator.update(0.1)
    assert [event.name for event in received] == ["hit"]


def test_animation_player_signals():
    world = World()
    player = AnimationPlayer("Player", world)
    player.add_animation(clip())
    frames = []
    events = []
    finished = []
    player.frame_changed.connect(lambda frame, index: frames.append(index))
    player.event.connect(events.append)
    player.finished.connect(finished.append)
    player.play("attack")
    player.update(0.1)
    player.update(0.2)
    assert frames[:2] == [0, 1]
    assert events[0].name == "hit"
    assert finished == ["attack"]


def test_animation_player_can_drive_animated_sprite_without_double_update():
    world = World()
    root = Node("Root", world)
    sprite = AnimatedSprite("Sprite", world)
    player = AnimationPlayer("AnimationPlayer", world)
    root.add_child(sprite)
    root.add_child(player)
    player.add_animation(clip(loop=True))
    player.bind_sprite(sprite)
    player.play("attack")
    root.update_tree(0.1)
    assert player.frame_index == 1
    assert sprite.animator is player.animator


def test_animation_state_machine_transitions():
    world = World()
    player = AnimationPlayer("Player", world)
    player.add_animation(clip("idle", loop=True))
    player.add_animation(clip("run", loop=True))
    machine = AnimationStateMachine(player)
    machine.add_state("idle", "idle")
    machine.add_state("run", "run")
    moving = {"value": False}
    machine.add_transition("idle", "run", lambda: moving["value"])
    machine.set_state("idle")
    assert player.current_animation_name == "idle"
    moving["value"] = True
    assert machine.update()
    assert machine.current_state == "run"
    assert player.current_animation_name == "run"


def test_state_machine_priority_is_deterministic():
    world = World()
    player = AnimationPlayer("Player", world)
    for name in ("idle", "walk", "attack"):
        player.add_animation(clip(name, loop=True))
    machine = AnimationStateMachine(player)
    for name in ("idle", "walk", "attack"):
        machine.add_state(name, name)
    machine.add_transition("idle", "walk", lambda: True, priority=0)
    machine.add_transition("idle", "attack", lambda: True, priority=10)
    machine.set_state("idle")
    machine.update()
    assert machine.current_state == "attack"


def test_animation_player_serialization_round_trip():
    world = World()
    registry = NodeFactoryRegistry()
    player = AnimationPlayer("Player", world)
    player.speed_scale = 1.5
    player.autoplay = "attack"
    player.target_node_name = "Sprite"
    player.add_animation(clip())
    state = registry.dump_properties(player)
    restored = registry.create("AnimationPlayer", "Restored", world)
    registry.load_properties(restored, state)
    assert restored.speed_scale == 1.5
    assert restored.autoplay == "attack"
    assert restored.target_node_name == "Sprite"
    restored_clip = restored.get_animation("attack")
    assert restored_clip is not None
    assert restored_clip.events[0].name == "hit"
    assert restored_clip.events[0].data == {"damage": 5}
