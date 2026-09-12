from __future__ import annotations

from dataclasses import dataclass

from nexora.nodes.node import Node
from nexora.tilemap import (
    TileCollision,
    TileMoveResult,
)


@dataclass(
    slots=True,
)
class Vector2:
    x: float = 0.0
    y: float = 0.0

    def set(
        self,
        x: float,
        y: float,
    ) -> None:
        self.x = float(
            x
        )

        self.y = float(
            y
        )

    def clear(
        self,
    ) -> None:
        self.x = 0.0
        self.y = 0.0

    @property
    def tuple(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.x,
            self.y,
        )


class CharacterBody2D(Node):
    """
    Kinematic 2D body using TileCollision.

    Position is stored in Node.transform.x/y.

    The collision box uses top-left world coordinates.

    transform.x / transform.y therefore represent the top-left
    corner of the body's collision rectangle.
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
        # Motion
        # ======================================================

        self.velocity = Vector2()

        # ======================================================
        # Collision shape
        # ======================================================

        self.collision_width: float = 32.0
        self.collision_height: float = 32.0

        # Optional local offset from transform position.
        self.collision_offset_x: float = 0.0
        self.collision_offset_y: float = 0.0

        # ======================================================
        # State
        # ======================================================

        self.is_on_floor: bool = False
        self.is_on_ceiling: bool = False
        self.is_on_wall: bool = False

        self.collided_left: bool = False
        self.collided_right: bool = False

        self.last_collision: TileMoveResult | None = None

    # ==============================================================
    # Collision rectangle
    # ==============================================================

    @property
    def collision_position(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.transform.x
            + self.collision_offset_x,

            self.transform.y
            + self.collision_offset_y,
        )

    @property
    def collision_size(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.collision_width,
            self.collision_height,
        )

    @property
    def collision_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        x, y = (
            self.collision_position
        )

        return (
            x,
            y,
            self.collision_width,
            self.collision_height,
        )

    # ==============================================================
    # Configuration
    # ==============================================================

    def set_collision_size(
        self,
        width: float,
        height: float,
    ) -> None:
        width = float(
            width
        )

        height = float(
            height
        )

        if width <= 0.0:
            raise ValueError(
                "collision width must be greater than zero."
            )

        if height <= 0.0:
            raise ValueError(
                "collision height must be greater than zero."
            )

        self.collision_width = width
        self.collision_height = height

    def set_collision_offset(
        self,
        x: float,
        y: float,
    ) -> None:
        self.collision_offset_x = float(
            x
        )

        self.collision_offset_y = float(
            y
        )

    # ==============================================================
    # Movement
    # ==============================================================

    def move_and_slide(
        self,
        collision: TileCollision,
        layer_name: str,
        delta_time: float,
    ) -> TileMoveResult:
        """
        Move the body using velocity and resolve collisions.

        velocity is interpreted as units per second.
        """

        delta_time = float(
            delta_time
        )

        if delta_time < 0.0:
            raise ValueError(
                "delta_time must be >= 0."
            )

        self._reset_collision_state()

        start_collision_x = (
            self.transform.x
            + self.collision_offset_x
        )

        start_collision_y = (
            self.transform.y
            + self.collision_offset_y
        )

        requested_dx = (
            self.velocity.x
            * delta_time
        )

        requested_dy = (
            self.velocity.y
            * delta_time
        )

        result = collision.move_aabb(
            layer_name,
            start_collision_x,
            start_collision_y,
            self.collision_width,
            self.collision_height,
            requested_dx,
            requested_dy,
        )

        # ======================================================
        # Apply resolved position
        # ======================================================

        self.transform.x = (
            result.x
            - self.collision_offset_x
        )

        self.transform.y = (
            result.y
            - self.collision_offset_y
        )

        # ======================================================
        # Collision state
        # ======================================================

        self.collided_left = (
            result.collided_left
        )

        self.collided_right = (
            result.collided_right
        )

        self.is_on_ceiling = (
            result.collided_top
        )

        self.is_on_floor = (
            result.collided_bottom
        )

        self.is_on_wall = (
            self.collided_left
            or self.collided_right
        )

        # ======================================================
        # Slide response
        # ======================================================

        if (
            result.collided_left
            or result.collided_right
        ):
            self.velocity.x = 0.0

        if (
            result.collided_top
            or result.collided_bottom
        ):
            self.velocity.y = 0.0

        self.last_collision = (
            result
        )

        return result

    # ==============================================================
    # Direct movement
    # ==============================================================

    def move_and_collide(
        self,
        collision: TileCollision,
        layer_name: str,
        dx: float,
        dy: float,
    ) -> TileMoveResult:
        """
        Move by explicit world-space delta.

        Unlike move_and_slide(), this method does not use velocity.
        """

        self._reset_collision_state()

        start_collision_x = (
            self.transform.x
            + self.collision_offset_x
        )

        start_collision_y = (
            self.transform.y
            + self.collision_offset_y
        )

        result = collision.move_aabb(
            layer_name,
            start_collision_x,
            start_collision_y,
            self.collision_width,
            self.collision_height,
            float(
                dx
            ),
            float(
                dy
            ),
        )

        self.transform.x = (
            result.x
            - self.collision_offset_x
        )

        self.transform.y = (
            result.y
            - self.collision_offset_y
        )

        self.collided_left = (
            result.collided_left
        )

        self.collided_right = (
            result.collided_right
        )

        self.is_on_ceiling = (
            result.collided_top
        )

        self.is_on_floor = (
            result.collided_bottom
        )

        self.is_on_wall = (
            self.collided_left
            or self.collided_right
        )

        self.last_collision = (
            result
        )

        return result

    # ==============================================================
    # State
    # ==============================================================

    def _reset_collision_state(
        self,
    ) -> None:
        self.is_on_floor = False
        self.is_on_ceiling = False
        self.is_on_wall = False

        self.collided_left = False
        self.collided_right = False

        self.last_collision = None