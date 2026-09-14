from __future__ import annotations

import math

from typing import TYPE_CHECKING

from nexora.nodes.node import Node
from nexora.nodes.entity.collision_shape_2d import (
    CollisionShape2D,
)
from nexora.physics import (
    get_physics_world,
)


if TYPE_CHECKING:
    from nexora.ecs.world import World


class Body2D(Node):
    """
    Base class for physics-related 2D bodies.

    Body2D owns collision configuration:

        - collision layer
        - collision mask
        - collision enabled state

    Collision geometry is supplied by CollisionShape2D children.

    Body2D itself contains no collision geometry.
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
        # Collision filtering
        # ======================================================

        self.collision_layer: int = 1
        self.collision_mask: int = 0xFFFFFFFF

        self.collision_enabled: bool = True

        # ======================================================
        # Physics world
        # ======================================================

        self._physics_world = (
            get_physics_world(
                world
            )
        )

        self._physics_world.register(
            self
        )

    # ==============================================================
    # Physics world
    # ==============================================================

    @property
    def physics_world(
        self,
    ):
        return self._physics_world

    # ==============================================================
    # Shapes
    # ==============================================================

    @property
    def collision_shapes(
        self,
    ) -> tuple[
        CollisionShape2D,
        ...,
    ]:
        """
        Return all direct CollisionShape2D children.
        """

        return tuple(
            child
            for child in self.children
            if isinstance(
                child,
                CollisionShape2D,
            )
        )

    @property
    def active_collision_shapes(
        self,
    ) -> tuple[
        CollisionShape2D,
        ...,
    ]:
        """
        Return all active collision shapes.
        """

        if not self.collision_enabled:
            return ()

        if not self.enabled:
            return ()

        return tuple(
            shape
            for shape in self.collision_shapes
            if (
                not shape.disabled
                and shape.enabled
            )
        )

    @property
    def primary_collision_shape(
        self,
    ) -> CollisionShape2D | None:
        """
        Return the first active CollisionShape2D.
        """

        shapes = (
            self.active_collision_shapes
        )

        if not shapes:
            return None

        return shapes[0]

    def require_collision_shape(
        self,
    ) -> CollisionShape2D:
        """
        Return the primary collision shape.

        Raises RuntimeError when no active CollisionShape2D exists.
        """

        shape = (
            self.primary_collision_shape
        )

        if shape is None:
            raise RuntimeError(
                f"{type(self).__name__} "
                f"'{self.name}' requires an active "
                "CollisionShape2D child."
            )

        return shape

    # ==============================================================
    # Combined collision bounds
    # ==============================================================

    @property
    def collision_aabb(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        """
        Return the combined world-space AABB of all active
        CollisionShape2D children.

        Multiple CollisionShape2D children are merged into one
        broadphase bounding box.

        Returns None when the body has no active shapes.
        """

        shapes = (
            self.active_collision_shapes
        )

        if not shapes:
            return None

        (
            first_x,
            first_y,
            first_width,
            first_height,
        ) = (
            shapes[0].world_rect
        )

        min_x = first_x
        min_y = first_y

        max_x = (
            first_x
            + first_width
        )

        max_y = (
            first_y
            + first_height
        )

        for shape in shapes[1:]:
            (
                x,
                y,
                width,
                height,
            ) = (
                shape.world_rect
            )

            min_x = min(
                min_x,
                x,
            )

            min_y = min(
                min_y,
                y,
            )

            max_x = max(
                max_x,
                x + width,
            )

            max_y = max(
                max_y,
                y + height,
            )

        return (
            min_x,
            min_y,
            max_x - min_x,
            max_y - min_y,
        )

    # ==============================================================
    # Collision layers
    # ==============================================================

    def set_collision_layer(
        self,
        layer: int,
    ) -> None:
        """
        Set the complete collision layer bitmask.
        """

        layer = int(
            layer
        )

        if layer < 0:
            raise ValueError(
                "collision_layer must be >= 0."
            )

        self.collision_layer = layer

    def set_collision_mask(
        self,
        mask: int,
    ) -> None:
        """
        Set the complete collision mask bitmask.
        """

        mask = int(
            mask
        )

        if mask < 0:
            raise ValueError(
                "collision_mask must be >= 0."
            )

        self.collision_mask = mask

    # ==============================================================
    # Layer helpers
    # ==============================================================

    def add_collision_layer(
        self,
        layer: int,
    ) -> None:
        self.collision_layer |= (
            self._layer_bit(
                layer
            )
        )

    def remove_collision_layer(
        self,
        layer: int,
    ) -> None:
        self.collision_layer &= ~(
            self._layer_bit(
                layer
            )
        )

    def has_collision_layer(
        self,
        layer: int,
    ) -> bool:
        return bool(
            self.collision_layer
            & self._layer_bit(
                layer
            )
        )

    # ==============================================================
    # Mask helpers
    # ==============================================================

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

    # ==============================================================
    # Filtering
    # ==============================================================

    def can_detect(
        self,
        other: Body2D,
    ) -> bool:
        """
        One-way collision filtering.
        """

        if other is self:
            return False

        if not self.collision_enabled:
            return False

        if not other.collision_enabled:
            return False

        return bool(
            self.collision_mask
            & other.collision_layer
        )

    def can_collide_with(
        self,
        other: Body2D,
    ) -> bool:
        """
        Two-way collision filtering.
        """

        if other is self:
            return False

        if not self.collision_enabled:
            return False

        if not other.collision_enabled:
            return False

        detects_other = bool(
            self.collision_mask
            & other.collision_layer
        )

        other_detects_self = bool(
            other.collision_mask
            & self.collision_layer
        )

        return (
            detects_other
            and other_detects_self
        )

    # ==============================================================
    # Shape intersection
    # ==============================================================

    def overlaps_body(
        self,
        other: Body2D,
    ) -> bool:
        """
        Test all active CollisionShape2D children against another
        Body2D.
        """

        if not self.can_collide_with(
            other
        ):
            return False

        own_shapes = (
            self.active_collision_shapes
        )

        other_shapes = (
            other.active_collision_shapes
        )

        if not own_shapes:
            return False

        if not other_shapes:
            return False

        for own_shape in own_shapes:
            for other_shape in other_shapes:
                if own_shape.overlaps(
                    other_shape
                ):
                    return True

        return False

    # ==============================================================
    # World position
    # ==============================================================

    def set_world_position(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Set the Body2D position in world coordinates.

        The local Node transform is calculated from the parent's
        world transform.
        """

        x = float(
            x
        )

        y = float(
            y
        )

        # ======================================================
        # Root / no parent
        # ======================================================

        if self.parent is None:
            self.transform.x = x
            self.transform.y = y

            self._physics_world.update_body(
                self
            )

            return

        # ======================================================
        # Parent transform
        # ======================================================

        parent_x, parent_y = (
            self.parent.world_position
        )

        parent_scale_x, parent_scale_y = (
            self.parent.world_scale
        )

        if parent_scale_x == 0.0:
            raise ValueError(
                "Parent world scale_x cannot be zero."
            )

        if parent_scale_y == 0.0:
            raise ValueError(
                "Parent world scale_y cannot be zero."
            )

        # ======================================================
        # World-space offset
        # ======================================================

        dx = (
            x
            - parent_x
        )

        dy = (
            y
            - parent_y
        )

        # ======================================================
        # Undo parent scale
        # ======================================================

        dx /= parent_scale_x
        dy /= parent_scale_y

        # ======================================================
        # Undo parent rotation
        # ======================================================

        angle = math.radians(
            -self.parent.world_rotation
        )

        cos_angle = math.cos(
            angle
        )

        sin_angle = math.sin(
            angle
        )

        local_x = (
            dx * cos_angle
            - dy * sin_angle
        )

        local_y = (
            dx * sin_angle
            + dy * cos_angle
        )

        # ======================================================
        # Apply local transform
        # ======================================================

        self.transform.x = local_x
        self.transform.y = local_y

        self._physics_world.update_body(
            self
        )

    def translate_world(
        self,
        dx: float,
        dy: float,
    ) -> None:
        """
        Move the Body2D by a world-space delta.
        """

        dx = float(
            dx
        )

        dy = float(
            dy
        )

        world_x, world_y = (
            self.world_position
        )

        self.set_world_position(
            world_x + dx,
            world_y + dy,
        )

    # ==============================================================
    # Physics synchronization
    # ==============================================================

    def sync_physics(
        self,
    ) -> None:
        """
        Update this body's broadphase proxy.

        Useful after direct transform or CollisionShape2D changes.
        """

        self._physics_world.update_body(
            self
        )

    # ==============================================================
    # Destroy
    # ==============================================================

    def destroy(
        self,
    ) -> None:
        """
        Remove the body from the physics registry and destroy the
        Node.
        """

        self._physics_world.unregister(
            self
        )

        super().destroy()

    # ==============================================================
    # Helpers
    # ==============================================================

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