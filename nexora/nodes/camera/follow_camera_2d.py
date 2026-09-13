from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes.camera.camera_2d import Camera2D
from nexora.nodes.node import Node


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


class FollowCamera2D(Camera2D):
    """
    Camera node that follows a target node.

    If no explicit target is assigned, the parent node
    can be used automatically as the follow target.

    Typical usage:

        camera = FollowCamera2D(
            "PlayerCamera",
            world,
            renderer,
        )

        player.add_child(camera)
    """

    def __init__(
        self,
        name: str,
        world,
        renderer: Renderer,
        *,
        target: Node | None = None,
    ) -> None:
        super().__init__(
            name,
            world,
            renderer,
        )

        self.target: Node | None = target

        self.follow_parent: bool = True

        self.smooth: float = 0.12

        self.offset_x: float = 0.0
        self.offset_y: float = 0.0

        self.center_on_collision: bool = True

        self.snap_on_first_update: bool = True

        self._has_position: bool = False

    # ==========================================================
    # Target
    # ==========================================================

    def set_target(
        self,
        target: Node | None,
    ) -> None:
        self.target = target
        self._has_position = False

    def clear_target(
        self,
    ) -> None:
        self.target = None
        self._has_position = False

    def _get_target(
        self,
    ) -> Node | None:
        if self.target is not None:
            return self.target

        if self.follow_parent:
            return self.parent

        return None

    # ==========================================================
    # Target position
    # ==========================================================

    def _get_target_position(
        self,
    ) -> tuple[float, float] | None:
        target = self._get_target()

        if target is None:
            return None

        x, y = target.world_position

        if self.center_on_collision:
            collision_width = getattr(
                target,
                "collision_width",
                None,
            )

            collision_height = getattr(
                target,
                "collision_height",
                None,
            )

            if (
                collision_width is not None
                and collision_height is not None
            ):
                collision_offset_x = getattr(
                    target,
                    "collision_offset_x",
                    0.0,
                )

                collision_offset_y = getattr(
                    target,
                    "collision_offset_y",
                    0.0,
                )

                x += (
                    collision_offset_x
                    + collision_width * 0.5
                )

                y += (
                    collision_offset_y
                    + collision_height * 0.5
                )

        x += self.offset_x
        y += self.offset_y

        return x, y

    # ==========================================================
    # Follow settings
    # ==========================================================

    def set_offset(
        self,
        x: float,
        y: float,
    ) -> None:
        self.offset_x = float(x)
        self.offset_y = float(y)

    def set_smoothing(
        self,
        smooth: float,
    ) -> None:
        smooth = float(smooth)

        if smooth < 0.0:
            raise ValueError(
                "Camera smoothing cannot be negative."
            )

        self.smooth = smooth

    # ==========================================================
    # Position
    # ==========================================================

    def snap_to_target(
        self,
    ) -> None:
        position = self._get_target_position()

        if position is None:
            return

        x, y = position

        self.set_position(
            x,
            y,
        )

        self._has_position = True

        self.clamp()

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self.active:
            return

        target_position = (
            self._get_target_position()
        )

        if target_position is not None:
            target_x, target_y = (
                target_position
            )

            if (
                self.snap_on_first_update
                and not self._has_position
            ):
                self.set_position(
                    target_x,
                    target_y,
                )

                self._has_position = True

            else:
                self.camera.follow(
                    target_x,
                    target_y,
                    smooth=self.smooth,
                    delta_time=delta_time,
                )

                self._has_position = True

        super().update(
            delta_time
        )