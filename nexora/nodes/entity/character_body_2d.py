from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nexora.nodes.entity.body_2d import (
    Body2D,
)

from nexora.physics import (
    KinematicCollision2D,
)

from nexora.tilemap import (
    TileCollision,
    TileMoveResult,
)


if TYPE_CHECKING:
    from nexora.ecs.world import World


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


@dataclass(
    slots=True,
)
class BodyMoveResult:
    """
    Result of CharacterBody2D movement against Body2D nodes.
    """

    movement_x: float = 0.0
    movement_y: float = 0.0

    collided_left: bool = False
    collided_right: bool = False
    collided_top: bool = False
    collided_bottom: bool = False

    collisions: tuple[
        KinematicCollision2D,
        ...,
    ] = ()

    # ==============================================================
    # Movement
    # ==============================================================

    @property
    def movement(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.movement_x,
            self.movement_y,
        )

    # ==============================================================
    # Collision state
    # ==============================================================

    @property
    def collided(
        self,
    ) -> bool:
        return bool(
            self.collisions
        )

    @property
    def collision_count(
        self,
    ) -> int:
        return len(
            self.collisions
        )

    # ==============================================================
    # Collider compatibility
    # ==============================================================

    @property
    def colliders(
        self,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        """
        Return unique colliding bodies.

        Kept as a convenience / compatibility API.
        """

        return tuple(
            dict.fromkeys(
                collision.collider
                for collision
                in self.collisions
            )
        )


class CharacterBody2D(Body2D):
    """
    Movable kinematic 2D body.

    Collision geometry comes from CollisionShape2D children.

    Node-tree physics:

        body.move_and_slide(
            delta_time
        )

    TileCollision compatibility:

        body.move_and_slide(
            collision,
            "collision",
            delta_time,
        )
    """

    def __init__(
        self,
        name: str,
        world: World,
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
        # Collision state
        # ======================================================

        self.is_on_floor: bool = False
        self.is_on_ceiling: bool = False
        self.is_on_wall: bool = False

        self.collided_left: bool = False
        self.collided_right: bool = False

        # ======================================================
        # Last collisions
        # ======================================================

        self.last_collision: (
            TileMoveResult | None
        ) = None

        self.last_body_collision: (
            BodyMoveResult | None
        ) = None

        self._slide_collisions: tuple[
            KinematicCollision2D,
            ...,
        ] = ()

    # ==============================================================
    # Main movement API
    # ==============================================================

    def move_and_slide(
        self,
        collision_or_delta_time:
            TileCollision | float,
        layer_name: str | None = None,
        delta_time: float | None = None,
    ) -> (
        TileMoveResult
        | BodyMoveResult
    ):
        """
        Move the CharacterBody2D.

        Node-tree physics:

            body.move_and_slide(
                delta_time
            )

        TileCollision:

            body.move_and_slide(
                collision,
                "collision",
                delta_time,
            )
        """

        # ======================================================
        # Node-tree physics
        # ======================================================

        if not isinstance(
            collision_or_delta_time,
            TileCollision,
        ):
            if (
                layer_name is not None
                or delta_time is not None
            ):
                raise TypeError(
                    "Node-tree move_and_slide expects only "
                    "delta_time."
                )

            return self._move_and_slide_bodies(
                float(
                    collision_or_delta_time
                )
            )

        # ======================================================
        # TileCollision
        # ======================================================

        if layer_name is None:
            raise TypeError(
                "layer_name is required when using TileCollision."
            )

        if delta_time is None:
            raise TypeError(
                "delta_time is required when using TileCollision."
            )

        return self._move_and_slide_tiles(
            collision_or_delta_time,
            layer_name,
            float(
                delta_time
            ),
        )

    # ==============================================================
    # Body movement
    # ==============================================================

    def _move_and_slide_bodies(
        self,
        delta_time: float,
    ) -> BodyMoveResult:
        delta_time = float(
            delta_time
        )

        if delta_time < 0.0:
            raise ValueError(
                "delta_time must be >= 0."
            )

        dx = (
            self.velocity.x
            * delta_time
        )

        dy = (
            self.velocity.y
            * delta_time
        )

        result = self.move_and_collide_bodies(
            dx,
            dy,
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

        return result

    def move_and_collide_bodies(
        self,
        dx: float,
        dy: float,
    ) -> BodyMoveResult:
        """
        Move against Body2D nodes found through PhysicsWorld2D.
        """

        dx = float(
            dx
        )

        dy = float(
            dy
        )

        self._reset_collision_state()

        blocking_bodies = (
            self._query_blocking_bodies(
                dx,
                dy,
            )
        )

        collisions: list[
            KinematicCollision2D
        ] = []

        # ======================================================
        # X axis
        # ======================================================

        allowed_dx = self._resolve_body_x(
            blocking_bodies,
            dx,
            dy,
            collisions,
        )

        if allowed_dx != 0.0:
            self.translate_world(
                allowed_dx,
                0.0,
            )

        # ======================================================
        # Y axis
        # ======================================================

        allowed_dy = self._resolve_body_y(
            blocking_bodies,
            dx,
            dy,
            allowed_dx,
            collisions,
        )

        if allowed_dy != 0.0:
            self.translate_world(
                0.0,
                allowed_dy,
            )

        # ======================================================
        # Result
        # ======================================================

        result = BodyMoveResult(
            movement_x=allowed_dx,
            movement_y=allowed_dy,
            collided_left=(
                dx < 0.0
                and allowed_dx != dx
            ),
            collided_right=(
                dx > 0.0
                and allowed_dx != dx
            ),
            collided_top=(
                dy < 0.0
                and allowed_dy != dy
            ),
            collided_bottom=(
                dy > 0.0
                and allowed_dy != dy
            ),
            collisions=tuple(
                collisions
            ),
        )

        self._apply_body_result(
            result
        )

        # Final synchronization.
        self.sync_physics()

        return result

    # ==============================================================
    # Broadphase
    # ==============================================================

    def _query_blocking_bodies(
        self,
        dx: float,
        dy: float,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        """
        Query possible blockers through PhysicsWorld2D.

        Area2D nodes are detection only and never block movement.
        """

        from nexora.nodes.entity.area_2d import (
            Area2D,
        )

        query_aabb = (
            self._movement_query_aabb(
                dx,
                dy,
            )
        )

        if query_aabb is None:
            return ()

        x, y, width, height = (
            query_aabb
        )

        candidates = (
            self.physics_world.query_aabb(
                x,
                y,
                width,
                height,
                exclude=self,
                tree_root=self.tree_root,
            )
        )

        result: list[
            Body2D
        ] = []

        for body in candidates:
            if isinstance(
                body,
                Area2D,
            ):
                continue

            if not body.enabled:
                continue

            if not body.collision_enabled:
                continue

            if not body.active_collision_shapes:
                continue

            if not self.can_collide_with(
                body
            ):
                continue

            result.append(
                body
            )

        return tuple(
            result
        )

    def _movement_query_aabb(
        self,
        dx: float,
        dy: float,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        """
        Return an AABB containing both current and destination
        bounds.

        This creates the broadphase swept region.
        """

        current = (
            self.collision_aabb
        )

        if current is None:
            return None

        x, y, width, height = (
            current
        )

        target_x = (
            x
            + dx
        )

        target_y = (
            y
            + dy
        )

        min_x = min(
            x,
            target_x,
        )

        min_y = min(
            y,
            target_y,
        )

        max_x = max(
            x + width,
            target_x + width,
        )

        max_y = max(
            y + height,
            target_y + height,
        )

        return (
            min_x,
            min_y,
            max_x - min_x,
            max_y - min_y,
        )

    # ==============================================================
    # X-axis collision
    # ==============================================================

    def _resolve_body_x(
        self,
        bodies: tuple[
            Body2D,
            ...,
        ],
        dx: float,
        requested_dy: float,
        collisions: list[
            KinematicCollision2D
        ],
    ) -> float:
        if dx == 0.0:
            return 0.0

        allowed_dx = dx

        best_collision: (
            KinematicCollision2D | None
        ) = None

        for own_shape in (
            self.active_collision_shapes
        ):
            (
                own_x,
                own_y,
                own_width,
                own_height,
            ) = (
                own_shape.world_rect
            )

            own_left = own_x
            own_right = (
                own_x
                + own_width
            )

            own_top = own_y
            own_bottom = (
                own_y
                + own_height
            )

            for body in bodies:
                for other_shape in (
                    body.active_collision_shapes
                ):
                    (
                        other_x,
                        other_y,
                        other_width,
                        other_height,
                    ) = (
                        other_shape.world_rect
                    )

                    other_left = other_x
                    other_right = (
                        other_x
                        + other_width
                    )

                    other_top = other_y
                    other_bottom = (
                        other_y
                        + other_height
                    )

                    # No overlap on perpendicular axis.
                    if not self._ranges_overlap(
                        own_top,
                        own_bottom,
                        other_top,
                        other_bottom,
                    ):
                        continue

                    # ==================================================
                    # Moving right
                    # ==================================================

                    if dx > 0.0:
                        if (
                            own_right
                            > other_left
                        ):
                            continue

                        distance = (
                            other_left
                            - own_right
                        )

                        if (
                            distance
                            > allowed_dx
                        ):
                            continue

                        allowed_dx = max(
                            0.0,
                            distance,
                        )

                        point_y = (
                            self._overlap_center(
                                own_top,
                                own_bottom,
                                other_top,
                                other_bottom,
                            )
                        )

                        best_collision = (
                            KinematicCollision2D(
                                collider=body,
                                local_shape=own_shape,
                                collider_shape=other_shape,
                                point_x=other_left,
                                point_y=point_y,
                                normal_x=-1.0,
                                normal_y=0.0,
                                travel_x=allowed_dx,
                                travel_y=0.0,
                                remainder_x=(
                                    dx
                                    - allowed_dx
                                ),
                                remainder_y=requested_dy,
                            )
                        )

                    # ==================================================
                    # Moving left
                    # ==================================================

                    else:
                        if (
                            own_left
                            < other_right
                        ):
                            continue

                        distance = (
                            other_right
                            - own_left
                        )

                        if (
                            distance
                            < allowed_dx
                        ):
                            continue

                        allowed_dx = min(
                            0.0,
                            distance,
                        )

                        point_y = (
                            self._overlap_center(
                                own_top,
                                own_bottom,
                                other_top,
                                other_bottom,
                            )
                        )

                        best_collision = (
                            KinematicCollision2D(
                                collider=body,
                                local_shape=own_shape,
                                collider_shape=other_shape,
                                point_x=other_right,
                                point_y=point_y,
                                normal_x=1.0,
                                normal_y=0.0,
                                travel_x=allowed_dx,
                                travel_y=0.0,
                                remainder_x=(
                                    dx
                                    - allowed_dx
                                ),
                                remainder_y=requested_dy,
                            )
                        )

        if (
            best_collision is not None
            and allowed_dx != dx
        ):
            collisions.append(
                best_collision
            )

        return allowed_dx

    # ==============================================================
    # Y-axis collision
    # ==============================================================

    def _resolve_body_y(
        self,
        bodies: tuple[
            Body2D,
            ...,
        ],
        requested_dx: float,
        dy: float,
        resolved_dx: float,
        collisions: list[
            KinematicCollision2D
        ],
    ) -> float:
        if dy == 0.0:
            return 0.0

        allowed_dy = dy

        best_collision: (
            KinematicCollision2D | None
        ) = None

        # X movement has already been applied.
        #
        # Reading the shapes again here is what creates
        # slide-along-wall behavior.

        for own_shape in (
            self.active_collision_shapes
        ):
            (
                own_x,
                own_y,
                own_width,
                own_height,
            ) = (
                own_shape.world_rect
            )

            own_left = own_x
            own_right = (
                own_x
                + own_width
            )

            own_top = own_y
            own_bottom = (
                own_y
                + own_height
            )

            for body in bodies:
                for other_shape in (
                    body.active_collision_shapes
                ):
                    (
                        other_x,
                        other_y,
                        other_width,
                        other_height,
                    ) = (
                        other_shape.world_rect
                    )

                    other_left = other_x
                    other_right = (
                        other_x
                        + other_width
                    )

                    other_top = other_y
                    other_bottom = (
                        other_y
                        + other_height
                    )

                    if not self._ranges_overlap(
                        own_left,
                        own_right,
                        other_left,
                        other_right,
                    ):
                        continue

                    # ==================================================
                    # Moving down
                    # ==================================================

                    if dy > 0.0:
                        if (
                            own_bottom
                            > other_top
                        ):
                            continue

                        distance = (
                            other_top
                            - own_bottom
                        )

                        if (
                            distance
                            > allowed_dy
                        ):
                            continue

                        allowed_dy = max(
                            0.0,
                            distance,
                        )

                        point_x = (
                            self._overlap_center(
                                own_left,
                                own_right,
                                other_left,
                                other_right,
                            )
                        )

                        best_collision = (
                            KinematicCollision2D(
                                collider=body,
                                local_shape=own_shape,
                                collider_shape=other_shape,
                                point_x=point_x,
                                point_y=other_top,
                                normal_x=0.0,
                                normal_y=-1.0,
                                travel_x=resolved_dx,
                                travel_y=allowed_dy,
                                remainder_x=(
                                    requested_dx
                                    - resolved_dx
                                ),
                                remainder_y=(
                                    dy
                                    - allowed_dy
                                ),
                            )
                        )

                    # ==================================================
                    # Moving up
                    # ==================================================

                    else:
                        if (
                            own_top
                            < other_bottom
                        ):
                            continue

                        distance = (
                            other_bottom
                            - own_top
                        )

                        if (
                            distance
                            < allowed_dy
                        ):
                            continue

                        allowed_dy = min(
                            0.0,
                            distance,
                        )

                        point_x = (
                            self._overlap_center(
                                own_left,
                                own_right,
                                other_left,
                                other_right,
                            )
                        )

                        best_collision = (
                            KinematicCollision2D(
                                collider=body,
                                local_shape=own_shape,
                                collider_shape=other_shape,
                                point_x=point_x,
                                point_y=other_bottom,
                                normal_x=0.0,
                                normal_y=1.0,
                                travel_x=resolved_dx,
                                travel_y=allowed_dy,
                                remainder_x=(
                                    requested_dx
                                    - resolved_dx
                                ),
                                remainder_y=(
                                    dy
                                    - allowed_dy
                                ),
                            )
                        )

        if (
            best_collision is not None
            and allowed_dy != dy
        ):
            collisions.append(
                best_collision
            )

        return allowed_dy

    # ==============================================================
    # TileCollision movement
    # ==============================================================

    def _move_and_slide_tiles(
        self,
        collision: TileCollision,
        layer_name: str,
        delta_time: float,
    ) -> TileMoveResult:
        delta_time = float(
            delta_time
        )

        if delta_time < 0.0:
            raise ValueError(
                "delta_time must be >= 0."
            )

        self._reset_collision_state()

        shape = (
            self.require_collision_shape()
        )

        (
            shape_x,
            shape_y,
            width,
            height,
        ) = (
            shape.world_rect
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
            shape_x,
            shape_y,
            width,
            height,
            requested_dx,
            requested_dy,
        )

        self._apply_shape_world_position(
            shape_x,
            shape_y,
            result.x,
            result.y,
        )

        self._apply_tile_result(
            result
        )

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

        return result

    # ==============================================================
    # Explicit TileCollision movement
    # ==============================================================

    def move_and_collide(
        self,
        collision: TileCollision,
        layer_name: str,
        dx: float,
        dy: float,
    ) -> TileMoveResult:
        self._reset_collision_state()

        shape = (
            self.require_collision_shape()
        )

        (
            shape_x,
            shape_y,
            width,
            height,
        ) = (
            shape.world_rect
        )

        result = collision.move_aabb(
            layer_name,
            shape_x,
            shape_y,
            width,
            height,
            float(
                dx
            ),
            float(
                dy
            ),
        )

        self._apply_shape_world_position(
            shape_x,
            shape_y,
            result.x,
            result.y,
        )

        self._apply_tile_result(
            result
        )

        return result

    # ==============================================================
    # Shape movement
    # ==============================================================

    def _apply_shape_world_position(
        self,
        old_shape_x: float,
        old_shape_y: float,
        new_shape_x: float,
        new_shape_y: float,
    ) -> None:
        dx = (
            new_shape_x
            - old_shape_x
        )

        dy = (
            new_shape_y
            - old_shape_y
        )

        self.translate_world(
            dx,
            dy,
        )

    # ==============================================================
    # Collision state
    # ==============================================================

    def _apply_tile_result(
        self,
        result: TileMoveResult,
    ) -> None:
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

        self.last_collision = result

        # Tile collisions currently do not create
        # KinematicCollision2D contacts.
        self._slide_collisions = ()

    def _apply_body_result(
        self,
        result: BodyMoveResult,
    ) -> None:
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

        self.last_body_collision = (
            result
        )

        self._slide_collisions = (
            result.collisions
        )

    def _reset_collision_state(
        self,
    ) -> None:
        self.is_on_floor = False
        self.is_on_ceiling = False
        self.is_on_wall = False

        self.collided_left = False
        self.collided_right = False

        self.last_collision = None
        self.last_body_collision = None

        self._slide_collisions = ()

    # ==============================================================
    # Slide collision queries
    # ==============================================================

    @property
    def slide_collisions(
        self,
    ) -> tuple[
        KinematicCollision2D,
        ...,
    ]:
        return self._slide_collisions

    @property
    def slide_collision_count(
        self,
    ) -> int:
        return len(
            self._slide_collisions
        )

    def get_slide_collision(
        self,
        index: int,
    ) -> KinematicCollision2D:
        """
        Return a slide collision by index.

        Raises IndexError when the index does not exist.
        """

        return self._slide_collisions[
            index
        ]

    def get_last_slide_collision(
        self,
    ) -> KinematicCollision2D | None:
        """
        Return the most recent body collision from the last
        movement operation.
        """

        if not self._slide_collisions:
            return None

        return self._slide_collisions[
            -1
        ]

    # ==============================================================
    # Helpers
    # ==============================================================

    @staticmethod
    def _ranges_overlap(
        a_min: float,
        a_max: float,
        b_min: float,
        b_max: float,
    ) -> bool:
        return (
            a_min < b_max
            and a_max > b_min
        )

    @staticmethod
    def _overlap_center(
        a_min: float,
        a_max: float,
        b_min: float,
        b_max: float,
    ) -> float:
        """
        Return the center of the overlapping portion of two ranges.
        """

        overlap_min = max(
            a_min,
            b_min,
        )

        overlap_max = min(
            a_max,
            b_max,
        )

        return (
            overlap_min
            + overlap_max
        ) * 0.5