from __future__ import annotations

from nexora.animation import (
    AnimationClip,
    AnimationFrame,
    AnimationSet,
    Animator,
)

from nexora.nodes.node import Node


class AnimatedSprite(Node):
    """
    Scene node that renders an animated sprite.

    AnimatedSprite combines:

        Node transform
        AnimationClip
        AnimationSet
        Animator
        Renderer.sprite()

    The texture is referenced but not owned by the node.
    """

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        # ======================================================
        # Sprite
        # ======================================================

        self.texture = None

        self.width: float = 64.0
        self.height: float = 64.0

        self.origin: tuple[
            float,
            float,
        ] = (
            0.5,
            0.5,
        )

        self.alpha: float = 1.0

        self.flip_x: bool = False
        self.flip_y: bool = False

        # Used when no animation is playing.
        #
        # Nexora UV format:
        #
        # (
        #     uv_x,
        #     uv_y,
        #     uv_width,
        #     uv_height,
        # )
        self.uv: tuple[
            float,
            float,
            float,
            float,
        ] = (
            0.0,
            0.0,
            1.0,
            1.0,
        )

        # ======================================================
        # Animation
        # ======================================================

        self.animator = Animator()

    # ==============================================================
    # Single animations
    # ==============================================================

    def add_animation(
        self,
        clip: AnimationClip,
    ) -> None:
        """
        Add one animation clip.
        """

        self.animator.add_clip(
            clip
        )

    def remove_animation(
        self,
        name: str,
    ) -> None:
        """
        Remove an animation clip.
        """

        self.animator.remove_clip(
            name
        )

    def has_animation(
        self,
        name: str,
    ) -> bool:
        """
        Check whether this sprite contains an animation.
        """

        return self.animator.has_clip(
            name
        )

    def get_animation(
        self,
        name: str,
    ) -> AnimationClip | None:
        """
        Return an animation clip by name.
        """

        return self.animator.get_clip(
            name
        )

    # ==============================================================
    # Animation sets
    # ==============================================================

    def add_animations(
        self,
        animations: AnimationSet,
        *,
        replace: bool = False,
    ) -> None:
        """
        Add every animation from an AnimationSet.

        If replace is False, duplicate animation names raise
        ValueError.

        If replace is True, existing animations with the same name
        are replaced.
        """

        for clip in animations:
            if self.animator.has_clip(
                clip.name
            ):
                if not replace:
                    raise ValueError(
                        f"Animation "
                        f"{clip.name!r} "
                        f"already exists."
                    )

                self.animator.remove_clip(
                    clip.name
                )

            self.animator.add_clip(
                clip
            )

    # ==============================================================
    # Playback
    # ==============================================================

    def play(
        self,
        name: str,
        *,
        restart: bool = False,
    ) -> None:
        """
        Play an animation by name.
        """

        self.animator.play(
            name,
            restart=restart,
        )

    def pause(
        self,
    ) -> None:
        """
        Pause the current animation.
        """

        self.animator.pause()

    def resume(
        self,
    ) -> None:
        """
        Resume the current animation.
        """

        self.animator.resume()

    def stop(
        self,
    ) -> None:
        """
        Stop the current animation.
        """

        self.animator.stop()

    def reset_animation(
        self,
    ) -> None:
        """
        Reset the current animation to its first frame.
        """

        self.animator.reset()

    # ==============================================================
    # Animation state
    # ==============================================================

    @property
    def current_animation(
        self,
    ) -> AnimationClip | None:
        return (
            self.animator.current_clip
        )

    @property
    def current_frame(
        self,
    ) -> AnimationFrame | None:
        return (
            self.animator.current_frame
        )

    @property
    def playing(
        self,
    ) -> bool:
        return (
            self.animator.playing
        )

    @property
    def animation_finished(
        self,
    ) -> bool:
        return (
            self.animator.finished
        )

    @property
    def animation_progress(
        self,
    ) -> float:
        return (
            self.animator.progress
        )

    @property
    def animation_speed(
        self,
    ) -> float:
        return (
            self.animator.speed
        )

    @animation_speed.setter
    def animation_speed(
        self,
        value: float,
    ) -> None:
        self.animator.speed = float(
            value
        )

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Advance the active animation.

        Called automatically through the Scene/Node lifecycle.
        """

        self.animator.update(
            delta_time
        )

    # ==============================================================
    # Render
    # ==============================================================

    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        """
        Render the current sprite frame.
        """

        if self.texture is None:
            return

        # ------------------------------------------------------
        # Determine UV
        # ------------------------------------------------------

        uv = self.uv

        frame = (
            self.animator.current_frame
        )

        if (
            frame is not None
            and frame.uv is not None
        ):
            uv = frame.uv

        # ------------------------------------------------------
        # World transform
        # ------------------------------------------------------

        transform = (
            self.world_transform
        )

        scale_x = (
            transform.scale_x
        )

        scale_y = (
            transform.scale_y
        )

        width = (
            self.width
            * abs(
                scale_x
            )
        )

        height = (
            self.height
            * abs(
                scale_y
            )
        )

        # Negative scale acts as an additional flip.
        flip_x = (
            self.flip_x
            ^ (
                scale_x < 0.0
            )
        )

        flip_y = (
            self.flip_y
            ^ (
                scale_y < 0.0
            )
        )

        # ------------------------------------------------------
        # Alpha
        # ------------------------------------------------------

        alpha = max(
            0.0,
            min(
                1.0,
                self.alpha,
            ),
        )

        # ------------------------------------------------------
        # Draw
        # ------------------------------------------------------

        renderer.sprite(
            self.texture,
            transform.x,
            transform.y,
            width=width,
            height=height,
            rotation=transform.rotation,
            origin=self.origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
        )