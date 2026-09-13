from __future__ import annotations

import pytest

from nexora.animation import (
    AnimationClip,
)
from nexora.ecs.world import World
from nexora.nodes import (
    AnimatedSprite,
)
from nexora.animation import (
    AnimationClip,
    AnimationSet,
)


class DummyRenderer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def sprite(
        self,
        texture,
        x,
        y,
        *,
        width,
        height,
        rotation,
        origin,
        alpha,
        flip_x,
        flip_y,
        uv,
    ) -> None:
        self.calls.append(
            {
                "texture": texture,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "rotation": rotation,
                "origin": origin,
                "alpha": alpha,
                "flip_x": flip_x,
                "flip_y": flip_y,
                "uv": uv,
            }
        )


def create_sprite() -> AnimatedSprite:
    world = World()

    return AnimatedSprite(
        "Sprite",
        world,
    )


def create_clip() -> AnimationClip:
    return AnimationClip.from_row(
        "walk",
        row=0,
        frame_count=4,
        columns=4,
        rows=1,
        fps=4.0,
    )


def test_animated_sprite_defaults():
    sprite = create_sprite()

    assert sprite.texture is None

    assert sprite.width == pytest.approx(
        64.0
    )

    assert sprite.height == pytest.approx(
        64.0
    )

    assert sprite.origin == pytest.approx(
        (
            0.5,
            0.5,
        )
    )

    assert sprite.alpha == pytest.approx(
        1.0
    )

    assert sprite.flip_x is False
    assert sprite.flip_y is False

    assert sprite.uv == pytest.approx(
        (
            0.0,
            0.0,
            1.0,
            1.0,
        )
    )


def test_add_animation():
    sprite = create_sprite()

    clip = create_clip()

    sprite.add_animation(
        clip
    )

    assert sprite.has_animation(
        "walk"
    )

    assert sprite.get_animation(
        "walk"
    ) is clip


def test_remove_animation():
    sprite = create_sprite()

    sprite.add_animation(
        create_clip()
    )

    sprite.remove_animation(
        "walk"
    )

    assert not sprite.has_animation(
        "walk"
    )


def test_play_animation():
    sprite = create_sprite()

    sprite.add_animation(
        create_clip()
    )

    sprite.play(
        "walk"
    )

    assert sprite.playing

    assert sprite.current_animation is not None
    assert sprite.current_animation.name == "walk"

    assert sprite.current_frame is not None
    assert sprite.current_frame.index == 0


def test_update_advances_animation():
    sprite = create_sprite()

    sprite.add_animation(
        create_clip()
    )

    sprite.play(
        "walk"
    )

    sprite.update(
        0.25
    )

    assert sprite.current_frame is not None
    assert sprite.current_frame.index == 1


def test_pause_and_resume():
    sprite = create_sprite()

    sprite.add_animation(
        create_clip()
    )

    sprite.play(
        "walk"
    )

    sprite.pause()

    sprite.update(
        1.0
    )

    assert sprite.current_frame is not None
    assert sprite.current_frame.index == 0

    sprite.resume()

    sprite.update(
        0.25
    )

    assert sprite.current_frame is not None
    assert sprite.current_frame.index == 1


def test_stop_animation():
    sprite = create_sprite()

    sprite.add_animation(
        create_clip()
    )

    sprite.play(
        "walk"
    )

    sprite.stop()

    assert not sprite.playing
    assert sprite.current_animation is None
    assert sprite.current_frame is None


def test_animation_speed_property():
    sprite = create_sprite()

    sprite.animation_speed = 2.5

    assert sprite.animation_speed == pytest.approx(
        2.5
    )

    assert sprite.animator.speed == pytest.approx(
        2.5
    )


def test_render_without_texture_does_nothing():
    sprite = create_sprite()

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    assert renderer.calls == []


def test_render_uses_static_uv_without_animation():
    sprite = create_sprite()

    texture = object()

    sprite.texture = texture

    sprite.uv = (
        0.25,
        0.5,
        0.25,
        0.5,
    )

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    assert len(
        renderer.calls
    ) == 1

    call = renderer.calls[0]

    assert call["texture"] is texture

    assert call["uv"] == pytest.approx(
        (
            0.25,
            0.5,
            0.25,
            0.5,
        )
    )


def test_render_uses_animation_frame_uv():
    sprite = create_sprite()

    sprite.texture = object()

    sprite.add_animation(
        create_clip()
    )

    sprite.play(
        "walk"
    )

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    assert renderer.calls[0]["uv"] == pytest.approx(
        (
            0.0,
            0.0,
            0.25,
            1.0,
        )
    )

    sprite.update(
        0.25
    )

    renderer.calls.clear()

    sprite.render(
        renderer,
        0.0,
    )

    assert renderer.calls[0]["uv"] == pytest.approx(
        (
            0.25,
            0.0,
            0.25,
            1.0,
        )
    )


def test_render_uses_world_position():
    sprite = create_sprite()

    sprite.texture = object()

    sprite.transform.x = 120.0
    sprite.transform.y = -80.0

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    call = renderer.calls[0]

    assert call["x"] == pytest.approx(
        120.0
    )

    assert call["y"] == pytest.approx(
        -80.0
    )


def test_render_uses_rotation():
    sprite = create_sprite()

    sprite.texture = object()

    sprite.transform.rotation = 45.0

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    assert renderer.calls[0][
        "rotation"
    ] == pytest.approx(
        45.0
    )


def test_render_uses_scale():
    sprite = create_sprite()

    sprite.texture = object()

    sprite.width = 100.0
    sprite.height = 50.0

    sprite.transform.scale_x = 2.0
    sprite.transform.scale_y = 3.0

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    call = renderer.calls[0]

    assert call["width"] == pytest.approx(
        200.0
    )

    assert call["height"] == pytest.approx(
        150.0
    )


def test_negative_scale_flips_sprite():
    sprite = create_sprite()

    sprite.texture = object()

    sprite.transform.scale_x = -1.0
    sprite.transform.scale_y = -1.0

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    call = renderer.calls[0]

    assert call["flip_x"] is True
    assert call["flip_y"] is True

    assert call["width"] == pytest.approx(
        64.0
    )

    assert call["height"] == pytest.approx(
        64.0
    )


def test_explicit_flip_combines_with_negative_scale():
    sprite = create_sprite()

    sprite.texture = object()

    sprite.flip_x = True

    sprite.transform.scale_x = -1.0

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    # XOR:
    #
    # explicit flip = True
    # negative scale = True
    #
    # result = False

    assert renderer.calls[0][
        "flip_x"
    ] is False


def test_alpha_is_clamped_to_zero():
    sprite = create_sprite()

    sprite.texture = object()
    sprite.alpha = -5.0

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    assert renderer.calls[0][
        "alpha"
    ] == pytest.approx(
        0.0
    )


def test_alpha_is_clamped_to_one():
    sprite = create_sprite()

    sprite.texture = object()
    sprite.alpha = 5.0

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    assert renderer.calls[0][
        "alpha"
    ] == pytest.approx(
        1.0
    )


def test_origin_is_forwarded_to_renderer():
    sprite = create_sprite()

    sprite.texture = object()

    sprite.origin = (
        0.0,
        1.0,
    )

    renderer = DummyRenderer()

    sprite.render(
        renderer,
        0.0,
    )

    assert renderer.calls[0][
        "origin"
    ] == pytest.approx(
        (
            0.0,
            1.0,
        )
    )


def test_parent_transform_affects_world_position():
    world = World()

    parent = AnimatedSprite(
        "Parent",
        world,
    )

    child = AnimatedSprite(
        "Child",
        world,
    )

    parent.add_child(
        child
    )

    parent.transform.x = 100.0
    parent.transform.y = 50.0

    child.transform.x = 20.0
    child.transform.y = 10.0

    child.texture = object()

    renderer = DummyRenderer()

    child.render(
        renderer,
        0.0,
    )

    call = renderer.calls[0]

    assert call["x"] == pytest.approx(
        120.0
    )

    assert call["y"] == pytest.approx(
        60.0
    )

# ==============================================================
# AnimationSet integration
# ==============================================================


def create_animation_set() -> AnimationSet:
    animations = AnimationSet(
        columns=8,
        rows=4,
    )

    animations.add_row(
        "idle",
        row=0,
        frame_count=4,
        fps=6.0,
    )

    animations.add_row(
        "walk",
        row=1,
        frame_count=6,
        fps=12.0,
    )

    animations.add_row(
        "attack",
        row=2,
        frame_count=5,
        fps=15.0,
        loop=False,
    )

    return animations


def test_add_animation_set():
    sprite = create_sprite()

    animations = (
        create_animation_set()
    )

    sprite.add_animations(
        animations
    )

    assert sprite.has_animation(
        "idle"
    )

    assert sprite.has_animation(
        "walk"
    )

    assert sprite.has_animation(
        "attack"
    )


def test_add_animation_set_preserves_clips():
    sprite = create_sprite()

    animations = (
        create_animation_set()
    )

    idle = animations.require(
        "idle"
    )

    walk = animations.require(
        "walk"
    )

    attack = animations.require(
        "attack"
    )

    sprite.add_animations(
        animations
    )

    assert sprite.get_animation(
        "idle"
    ) is idle

    assert sprite.get_animation(
        "walk"
    ) is walk

    assert sprite.get_animation(
        "attack"
    ) is attack


def test_animation_set_clips_can_be_played():
    sprite = create_sprite()

    sprite.add_animations(
        create_animation_set()
    )

    sprite.play(
        "walk"
    )

    assert sprite.current_animation is not None

    assert (
        sprite.current_animation.name
        == "walk"
    )

    assert sprite.current_frame is not None

    assert sprite.current_frame.index == 8


def test_animation_set_non_looping_clip_preserved():
    sprite = create_sprite()

    sprite.add_animations(
        create_animation_set()
    )

    attack = sprite.get_animation(
        "attack"
    )

    assert attack is not None

    assert attack.loop is False


def test_add_animation_set_duplicate_raises():
    sprite = create_sprite()

    sprite.add_animation(
        AnimationClip.from_row(
            "walk",
            row=0,
            frame_count=4,
            columns=8,
            rows=4,
            fps=10.0,
        )
    )

    animations = (
        create_animation_set()
    )

    with pytest.raises(
        ValueError
    ):
        sprite.add_animations(
            animations
        )


def test_add_animation_set_replace_existing():
    sprite = create_sprite()

    old_walk = (
        AnimationClip.from_row(
            "walk",
            row=0,
            frame_count=2,
            columns=8,
            rows=4,
            fps=4.0,
        )
    )

    sprite.add_animation(
        old_walk
    )

    animations = (
        create_animation_set()
    )

    new_walk = (
        animations.require(
            "walk"
        )
    )

    sprite.add_animations(
        animations,
        replace=True,
    )

    assert sprite.get_animation(
        "walk"
    ) is new_walk

    assert sprite.get_animation(
        "walk"
    ) is not old_walk


def test_replace_animation_set_keeps_other_clips():
    sprite = create_sprite()

    sprite.add_animation(
        AnimationClip.from_row(
            "special",
            row=3,
            frame_count=2,
            columns=8,
            rows=4,
            fps=8.0,
        )
    )

    sprite.add_animations(
        create_animation_set(),
        replace=True,
    )

    assert sprite.has_animation(
        "special"
    )

    assert sprite.has_animation(
        "idle"
    )

    assert sprite.has_animation(
        "walk"
    )

    assert sprite.has_animation(
        "attack"
    )


def test_animation_set_multiple_play_switches():
    sprite = create_sprite()

    sprite.add_animations(
        create_animation_set()
    )

    sprite.play(
        "idle"
    )

    assert sprite.current_animation is not None

    assert (
        sprite.current_animation.name
        == "idle"
    )

    sprite.play(
        "walk"
    )

    assert sprite.current_animation is not None

    assert (
        sprite.current_animation.name
        == "walk"
    )

    sprite.play(
        "attack"
    )

    assert sprite.current_animation is not None

    assert (
        sprite.current_animation.name
        == "attack"
    )


def test_animation_set_update_uses_selected_clip():
    sprite = create_sprite()

    sprite.add_animations(
        create_animation_set()
    )

    sprite.play(
        "walk"
    )

    assert sprite.current_frame is not None

    assert sprite.current_frame.index == 8

    sprite.update(
        1.0 / 12.0
    )

    assert sprite.current_frame is not None

    assert sprite.current_frame.index == 9


def test_animation_set_attack_finishes():
    sprite = create_sprite()

    sprite.add_animations(
        create_animation_set()
    )

    sprite.play(
        "attack"
    )

    sprite.update(
        10.0
    )

    assert sprite.animation_finished

    assert not sprite.playing

    assert sprite.current_frame is not None

    # row 2 on an 8-column sheet:
    #
    # first frame = 16
    #
    # 5 frames:
    #
    # 16, 17, 18, 19, 20

    assert sprite.current_frame.index == 20

    