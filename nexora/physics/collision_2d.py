from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nexora.nodes.entity.body_2d import Body2D
    from nexora.nodes.entity.collision_shape_2d import (
        CollisionShape2D,
    )


@dataclass(
    slots=True,
    frozen=True,
)
class KinematicCollision2D:
    """
    Information about one kinematic collision.

    Coordinates and vectors are expressed in world space.
    """

    collider: Body2D

    local_shape: CollisionShape2D
    collider_shape: CollisionShape2D

    point_x: float
    point_y: float

    normal_x: float
    normal_y: float

    travel_x: float
    travel_y: float

    remainder_x: float
    remainder_y: float

    # ==============================================================
    # Convenience properties
    # ==============================================================

    @property
    def point(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.point_x,
            self.point_y,
        )

    @property
    def normal(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.normal_x,
            self.normal_y,
        )

    @property
    def travel(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.travel_x,
            self.travel_y,
        )

    @property
    def remainder(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.remainder_x,
            self.remainder_y,
        )

    # ==============================================================
    # Direction helpers
    # ==============================================================

    @property
    def is_left(
        self,
    ) -> bool:
        return self.normal_x > 0.0

    @property
    def is_right(
        self,
    ) -> bool:
        return self.normal_x < 0.0

    @property
    def is_top(
        self,
    ) -> bool:
        return self.normal_y > 0.0

    @property
    def is_bottom(
        self,
    ) -> bool:
        return self.normal_y < 0.0