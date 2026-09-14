from __future__ import annotations

import math

from typing import TYPE_CHECKING

from nexora.nodes.node import Node

from nexora.physics import (
    RayCastHit2D,
    get_physics_world,
)


if TYPE_CHECKING:
    from nexora.ecs.world import World
    from nexora.nodes.entity.body_2d import Body2D
    from nexora.nodes.entity.collision_shape_2d import (
        CollisionShape2D,
    )


class RayCast2D(Node):
    """
    Physics ray query node.

    RayCast2D uses PhysicsWorld2D for broadphase candidate lookup
    and CollisionShape2D rectangles for the narrowphase.

    Typical uses:

        - player interaction
        - line of sight
        - bullets / hitscan
        - AI vision
        - ground checks
        - obstacle detection

    The ray starts at this Node's world position.

    target_x / target_y describe the endpoint relative to the
    RayCast2D node.
    """

    def __init__(
        self,
        name: str,
        world: World,
        *,
        target_x: float = 64.0,
        target_y: float = 0.0,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        # ======================================================
        # Ray
        # ======================================================

        self.target_x: float = float(
            target_x
        )

        self.target_y: float = float(
            target_y
        )

        # ======================================================
        # Filtering
        # ======================================================

        self.collision_mask: int = (
            0xFFFFFFFF
        )

        self.collide_with_bodies: bool = True
        self.collide_with_areas: bool = True

        # Ignore the nearest Body2D ancestor.
        #
        # Important for:
        #
        # Player
        # └── RayCast2D
        #
        self.exclude_parent_body: bool = True

        # ======================================================
        # Query
        # ======================================================

        self.raycast_enabled: bool = True

        self._hit: (
            RayCastHit2D | None
        ) = None

        self._exceptions: set[
            Body2D
        ] = set()

        self._physics_world = (
            get_physics_world(
                world
            )
        )

    # ==============================================================
    # Fixed update
    # ==============================================================

    def fixed_update(
        self,
        delta_time: float,
    ) -> None:
        super().fixed_update(
            delta_time
        )

        if not self.raycast_enabled:
            self._hit = None
            return

        self.force_raycast_update()

    # ==============================================================
    # Target
    # ==============================================================

    def set_target(
        self,
        x: float,
        y: float,
    ) -> None:
        self.target_x = float(
            x
        )

        self.target_y = float(
            y
        )

    @property
    def target(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            self.target_x,
            self.target_y,
        )

    # ==============================================================
    # World ray
    # ==============================================================

    @property
    def ray_origin(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        return self.world_position

    @property
    def ray_end(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        """
        Return the ray endpoint in world coordinates.

        The local target vector follows this node's world rotation
        and scale.
        """

        origin_x, origin_y = (
            self.world_position
        )

        scale_x, scale_y = (
            self.world_scale
        )

        local_x = (
            self.target_x
            * scale_x
        )

        local_y = (
            self.target_y
            * scale_y
        )

        angle = math.radians(
            self.world_rotation
        )

        cos_angle = math.cos(
            angle
        )

        sin_angle = math.sin(
            angle
        )

        world_dx = (
            local_x * cos_angle
            - local_y * sin_angle
        )

        world_dy = (
            local_x * sin_angle
            + local_y * cos_angle
        )

        return (
            origin_x
            + world_dx,

            origin_y
            + world_dy,
        )

    @property
    def ray_length(
        self,
    ) -> float:
        origin_x, origin_y = (
            self.ray_origin
        )

        end_x, end_y = (
            self.ray_end
        )

        return math.hypot(
            end_x - origin_x,
            end_y - origin_y,
        )

    # ==============================================================
    # Query
    # ==============================================================

    def force_raycast_update(
        self,
    ) -> RayCastHit2D | None:
        """
        Immediately execute the ray query.

        Returns the nearest hit or None.
        """

        if not self.raycast_enabled:
            self._hit = None
            return None

        origin_x, origin_y = (
            self.ray_origin
        )

        end_x, end_y = (
            self.ray_end
        )

        direction_x = (
            end_x
            - origin_x
        )

        direction_y = (
            end_y
            - origin_y
        )

        length = math.hypot(
            direction_x,
            direction_y,
        )

        if length <= 0.0:
            self._hit = None
            return None

        candidates = (
            self._query_candidates(
                origin_x,
                origin_y,
                end_x,
                end_y,
            )
        )

        nearest_hit: (
            RayCastHit2D | None
        ) = None

        nearest_fraction = (
            math.inf
        )

        for body in candidates:
            for shape in (
                body.active_collision_shapes
            ):
                result = (
                    self._intersect_shape(
                        origin_x,
                        origin_y,
                        direction_x,
                        direction_y,
                        shape,
                    )
                )

                if result is None:
                    continue

                (
                    fraction,
                    normal_x,
                    normal_y,
                ) = result

                if (
                    fraction
                    >= nearest_fraction
                ):
                    continue

                point_x = (
                    origin_x
                    + direction_x
                    * fraction
                )

                point_y = (
                    origin_y
                    + direction_y
                    * fraction
                )

                nearest_fraction = fraction

                nearest_hit = RayCastHit2D(
                    collider=body,
                    collider_shape=shape,
                    point_x=point_x,
                    point_y=point_y,
                    normal_x=normal_x,
                    normal_y=normal_y,
                    distance=(
                        length
                        * fraction
                    ),
                    fraction=fraction,
                )

        self._hit = (
            nearest_hit
        )

        return nearest_hit

    # ==============================================================
    # Broadphase
    # ==============================================================

    def _query_candidates(
        self,
        origin_x: float,
        origin_y: float,
        end_x: float,
        end_y: float,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        from nexora.nodes.entity.area_2d import (
            Area2D,
        )

        from nexora.nodes.entity.body_2d import (
            Body2D,
        )

        # Very small padding ensures horizontal / vertical rays
        # still produce a valid broadphase rectangle.

        padding = 0.001

        min_x = min(
            origin_x,
            end_x,
        ) - padding

        min_y = min(
            origin_y,
            end_y,
        ) - padding

        max_x = max(
            origin_x,
            end_x,
        ) + padding

        max_y = max(
            origin_y,
            end_y,
        ) + padding

        width = (
            max_x
            - min_x
        )

        height = (
            max_y
            - min_y
        )

        owner = (
            self._find_owner_body()
            if self.exclude_parent_body
            else None
        )

        candidates = (
            self._physics_world.query_aabb(
                min_x,
                min_y,
                width,
                height,
                exclude=owner,
                tree_root=self.tree_root,
            )
        )

        result: list[
            Body2D
        ] = []

        for body in candidates:
            if body in self._exceptions:
                continue

            if not body.enabled:
                continue

            if not body.collision_enabled:
                continue

            if not body.active_collision_shapes:
                continue

            if (
                self.collision_mask
                & body.collision_layer
            ) == 0:
                continue

            if isinstance(
                body,
                Area2D,
            ):
                if not self.collide_with_areas:
                    continue

                if not body.monitorable:
                    continue

            else:
                if not self.collide_with_bodies:
                    continue

            result.append(
                body
            )

        return tuple(
            result
        )

    # ==============================================================
    # Ray / AABB narrowphase
    # ==============================================================

    @staticmethod
    def _intersect_shape(
        origin_x: float,
        origin_y: float,
        direction_x: float,
        direction_y: float,
        shape: CollisionShape2D,
    ) -> tuple[
        float,
        float,
        float,
    ] | None:
        """
        Segment vs AABB using the slab algorithm.

        Returns:

            fraction,
            normal_x,
            normal_y

        fraction is in range 0..1.
        """

        (
            rect_x,
            rect_y,
            width,
            height,
        ) = (
            shape.world_rect
        )

        min_x = rect_x
        min_y = rect_y

        max_x = (
            rect_x
            + width
        )

        max_y = (
            rect_y
            + height
        )

        t_enter = 0.0
        t_exit = 1.0

        normal_x = 0.0
        normal_y = 0.0

        epsilon = 1e-12

        # ======================================================
        # X slab
        # ======================================================

        if abs(
            direction_x
        ) < epsilon:
            if (
                origin_x < min_x
                or origin_x > max_x
            ):
                return None

        else:
            inverse_x = (
                1.0
                / direction_x
            )

            tx1 = (
                min_x
                - origin_x
            ) * inverse_x

            tx2 = (
                max_x
                - origin_x
            ) * inverse_x

            if tx1 <= tx2:
                x_enter = tx1
                x_exit = tx2

                x_normal = (
                    -1.0,
                    0.0,
                )

            else:
                x_enter = tx2
                x_exit = tx1

                x_normal = (
                    1.0,
                    0.0,
                )

            if x_enter > t_enter:
                t_enter = x_enter

                normal_x = (
                    x_normal[0]
                )

                normal_y = (
                    x_normal[1]
                )

            t_exit = min(
                t_exit,
                x_exit,
            )

            if t_enter > t_exit:
                return None

        # ======================================================
        # Y slab
        # ======================================================

        if abs(
            direction_y
        ) < epsilon:
            if (
                origin_y < min_y
                or origin_y > max_y
            ):
                return None

        else:
            inverse_y = (
                1.0
                / direction_y
            )

            ty1 = (
                min_y
                - origin_y
            ) * inverse_y

            ty2 = (
                max_y
                - origin_y
            ) * inverse_y

            if ty1 <= ty2:
                y_enter = ty1
                y_exit = ty2

                y_normal = (
                    0.0,
                    -1.0,
                )

            else:
                y_enter = ty2
                y_exit = ty1

                y_normal = (
                    0.0,
                    1.0,
                )

            if y_enter > t_enter:
                t_enter = y_enter

                normal_x = (
                    y_normal[0]
                )

                normal_y = (
                    y_normal[1]
                )

            t_exit = min(
                t_exit,
                y_exit,
            )

            if t_enter > t_exit:
                return None

        # ======================================================
        # Segment range
        # ======================================================

        if t_exit < 0.0:
            return None

        if t_enter > 1.0:
            return None

        t_enter = max(
            0.0,
            t_enter,
        )

        return (
            t_enter,
            normal_x,
            normal_y,
        )

    # ==============================================================
    # Owner
    # ==============================================================

    def _find_owner_body(
        self,
    ) -> Body2D | None:
        """
        Return the nearest Body2D ancestor.
        """

        from nexora.nodes.entity.body_2d import (
            Body2D,
        )

        node = (
            self.parent
        )

        while node is not None:
            if isinstance(
                node,
                Body2D,
            ):
                return node

            node = (
                node.parent
            )

        return None

    # ==============================================================
    # Result API
    # ==============================================================

    @property
    def is_colliding(
        self,
    ) -> bool:
        return (
            self._hit
            is not None
        )

    @property
    def collision(
        self,
    ) -> RayCastHit2D | None:
        return self._hit

    def get_collider(
        self,
    ) -> Body2D | None:
        if self._hit is None:
            return None

        return (
            self._hit.collider
        )

    def get_collider_shape(
        self,
    ) -> CollisionShape2D | None:
        if self._hit is None:
            return None

        return (
            self._hit.collider_shape
        )

    def get_collision_point(
        self,
    ) -> tuple[
        float,
        float,
    ] | None:
        if self._hit is None:
            return None

        return (
            self._hit.point
        )

    def get_collision_normal(
        self,
    ) -> tuple[
        float,
        float,
    ] | None:
        if self._hit is None:
            return None

        return (
            self._hit.normal
        )

    def get_collision_distance(
        self,
    ) -> float | None:
        if self._hit is None:
            return None

        return (
            self._hit.distance
        )

    # ==============================================================
    # Exceptions
    # ==============================================================

    def add_exception(
        self,
        body: Body2D,
    ) -> None:
        self._exceptions.add(
            body
        )

    def remove_exception(
        self,
        body: Body2D,
    ) -> None:
        self._exceptions.discard(
            body
        )

    def clear_exceptions(
        self,
    ) -> None:
        self._exceptions.clear()

    @property
    def exceptions(
        self,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        return tuple(
            self._exceptions
        )

    # ==============================================================
    # Mask
    # ==============================================================

    def set_collision_mask(
        self,
        mask: int,
    ) -> None:
        mask = int(
            mask
        )

        if mask < 0:
            raise ValueError(
                "collision_mask must be >= 0."
            )

        self.collision_mask = (
            mask
        )

    def add_collision_mask(
        self,
        layer: int,
    ) -> None:
        self.collision_mask |= (
            self._layer_bit(
                layer
            )
        )

    def remove_collision_mask(
        self,
        layer: int,
    ) -> None:
        self.collision_mask &= ~(
            self._layer_bit(
                layer
            )
        )

    def has_collision_mask(
        self,
        layer: int,
    ) -> bool:
        return bool(
            self.collision_mask
            & self._layer_bit(
                layer
            )
        )

    @staticmethod
    def _layer_bit(
        layer: int,
    ) -> int:
        layer = int(
            layer
        )

        if layer <= 0:
            raise ValueError(
                "Collision layer number must be greater than zero."
            )

        return (
            1
            << (
                layer - 1
            )
        )