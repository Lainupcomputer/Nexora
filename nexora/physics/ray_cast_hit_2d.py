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
class RayCastHit2D:
    """
    Result of a RayCast2D intersection.

    All coordinates are expressed in world space.
    """

    collider: Body2D
    collider_shape: CollisionShape2D

    point_x: float
    point_y: float

    normal_x: float
    normal_y: float

    distance: float

    fraction: float

    # ==============================================================
    # Convenience
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