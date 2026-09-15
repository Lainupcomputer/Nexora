from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.animation.animator import Animator
from nexora.animation.clip import AnimationClip, AnimationEvent, AnimationFrame
from nexora.nodes.node import Node

if TYPE_CHECKING:
    from nexora.nodes.texture.animated_sprite import AnimatedSprite


class AnimationPlayer(Node):
    """Node-based animation playback service.

    The player owns one :class:`Animator` and can optionally drive an
    ``AnimatedSprite``. It exposes Nexora Signals for frame changes,
    frame events, playback start and completion.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.animator = Animator()
        self.animation_started = self.create_signal("animation_started")
        self.frame_changed = self.create_signal("frame_changed")
        self.event = self.create_signal("animation_event")
        self.finished = self.create_signal("animation_finished")

        self.autoplay: str | None = None
        self.target_node_name: str | None = None
        self._target: AnimatedSprite | None = None
        self._autoplay_started = False

        self.animator.on_frame_changed = self._on_frame_changed
        self.animator.on_event = self._on_event
        self.animator.on_finished = self._on_finished

    def add_animation(self, clip: AnimationClip, *, replace: bool = False) -> None:
        if self.animator.has_clip(clip.name) and not replace:
            raise ValueError(f"Animation {clip.name!r} already exists.")
        if replace:
            self.animator.remove_clip(clip.name)
        self.animator.add_clip(clip)

    def remove_animation(self, name: str) -> None:
        self.animator.remove_clip(name)

    def get_animation(self, name: str) -> AnimationClip | None:
        return self.animator.get_clip(name)

    def has_animation(self, name: str) -> bool:
        return self.animator.has_clip(name)

    @property
    def animations(self) -> tuple[AnimationClip, ...]:
        return tuple(self.animator._clips.values())

    def bind_sprite(self, sprite: AnimatedSprite | None) -> None:
        if self._target is sprite:
            return
        if self._target is not None:
            self._target._external_animation_driver = False
        self._target = sprite
        if sprite is None:
            self.target_node_name = None
            return
        if sprite.world is not self.world:
            raise ValueError("AnimationPlayer target belongs to a different world.")
        self.target_node_name = sprite.name
        sprite.animator = self.animator
        sprite._external_animation_driver = True

    @property
    def target(self) -> AnimatedSprite | None:
        return self._target

    def _resolve_target(self) -> None:
        if self._target is not None or not self.target_node_name:
            return
        from nexora.nodes.texture.animated_sprite import AnimatedSprite
        root = self.tree_root
        candidate = root if root.name == self.target_node_name else root.find_child(self.target_node_name)
        if isinstance(candidate, AnimatedSprite):
            self.bind_sprite(candidate)

    def play(self, name: str, *, restart: bool = False) -> None:
        previous = self.current_animation_name
        self.animator.play(name, restart=restart)
        if restart or previous != name:
            self.animation_started.emit(name)

    def pause(self) -> None:
        self.animator.pause()

    def resume(self) -> None:
        self.animator.resume()

    def stop(self) -> None:
        self.animator.stop()

    def reset_animation(self) -> None:
        self.animator.reset()

    @property
    def speed_scale(self) -> float:
        return self.animator.speed_scale

    @speed_scale.setter
    def speed_scale(self, value: float) -> None:
        self.animator.speed_scale = value

    @property
    def current_animation(self) -> AnimationClip | None:
        return self.animator.current_clip

    @property
    def current_animation_name(self) -> str | None:
        clip = self.current_animation
        return None if clip is None else clip.name

    @property
    def current_frame(self) -> AnimationFrame | None:
        return self.animator.current_frame

    @property
    def frame_index(self) -> int:
        return self.animator.frame_index

    @property
    def playing(self) -> bool:
        return self.animator.playing

    @property
    def animation_finished(self) -> bool:
        return self.animator.finished

    def update(self, delta_time: float) -> None:
        self._resolve_target()
        if not self._autoplay_started and self.autoplay:
            self._autoplay_started = True
            if self.has_animation(self.autoplay):
                self.play(self.autoplay)
        self.animator.update(delta_time)

    def _on_frame_changed(self, frame: AnimationFrame) -> None:
        self.frame_changed.emit(frame, self.animator.frame_index)

    def _on_event(self, event: AnimationEvent) -> None:
        self.event.emit(event)

    def _on_finished(self, clip: AnimationClip) -> None:
        self.finished.emit(clip.name)

    def destroy(self) -> None:
        if self._target is not None:
            self._target._external_animation_driver = False
            self._target = None
        super().destroy()
