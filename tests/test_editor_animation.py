from nexora.animation import AnimationClip, AnimationFrame
from nexora.ecs.world import World
from nexora.editor.commands import AnimationClipCommand, CommandStack
from nexora.nodes.texture.animated_sprite import AnimatedSprite
from nexora.scene.serialization.registry import NodeFactoryRegistry


def make_clip(name="idle"):
    return AnimationClip(
        name=name,
        frames=(
            AnimationFrame(index=0, duration=0.1),
            AnimationFrame(index=1, duration=0.2),
        ),
    )


def test_animation_clip_command_supports_undo_and_redo_for_animated_sprite():
    sprite = AnimatedSprite("Hero", World())
    stack = CommandStack()
    stack.execute(AnimationClipCommand(sprite, make_clip()))

    assert [clip.name for clip in sprite.animations] == ["idle"]
    stack.undo()
    assert sprite.animations == ()
    stack.redo()
    assert sprite.get_animation("idle").frame_count == 2


def test_animated_sprite_animation_clips_round_trip_through_scene_registry():
    registry = NodeFactoryRegistry()
    sprite = AnimatedSprite("Hero", World())
    sprite.add_animation(make_clip())

    state = registry.dump_properties(sprite)
    restored = registry.create("AnimatedSprite", "Restored", World())
    registry.load_properties(restored, state)

    restored_clip = restored.get_animation("idle")
    assert restored_clip is not None
    assert restored_clip.frames[1].duration == 0.2
