from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from nexora.nodes.entity.body_2d import (
    Body2D,
)


if TYPE_CHECKING:
    from nexora.ecs.world import World


BodyCallback = Callable[
    [Body2D],
    None,
]


class Area2D(Body2D):
    """
    Non-blocking collision detection area.

    Area2D uses PhysicsWorld2D broadphase queries to detect
    overlapping Body2D nodes.

    Area2D never blocks CharacterBody2D movement.
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
        # Monitoring
        # ======================================================

        self.monitoring: bool = True
        self.monitorable: bool = True

        # ======================================================
        # Current overlap state
        # ======================================================

        self._overlapping_bodies: set[
            Body2D
        ] = set()

        # ======================================================
        # Callbacks
        # ======================================================

        self._body_entered_callbacks: list[
            BodyCallback
        ] = []

        self._body_exited_callbacks: list[
            BodyCallback
        ] = []

    # ==============================================================
    # Update
    # ==============================================================

    def fixed_update(
        self,
        delta_time: float,
    ) -> None:
        """
        Update Area2D overlap state during the fixed physics step.
        """

        super().fixed_update(
            delta_time
        )

        self.update_overlaps()

    # ==============================================================
    # Overlap update
    # ==============================================================

    def update_overlaps(
        self,
    ) -> None:
        """
        Detect overlap changes and emit enter / exit callbacks.
        """

        if not self.monitoring:
            if self._overlapping_bodies:
                previous = tuple(
                    self._overlapping_bodies
                )

                self._overlapping_bodies.clear()

                for body in previous:
                    self._emit_body_exited(
                        body
                    )

            return

        current = set(
            self._collect_overlapping_bodies()
        )

        entered = (
            current
            - self._overlapping_bodies
        )

        exited = (
            self._overlapping_bodies
            - current
        )

        self._overlapping_bodies = current

        for body in entered:
            self._emit_body_entered(
                body
            )

        for body in exited:
            self._emit_body_exited(
                body
            )

    # ==============================================================
    # Broadphase query
    # ==============================================================

    def _collect_overlapping_bodies(
        self,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        """
        Query potentially overlapping bodies through PhysicsWorld2D
        and perform exact CollisionShape2D overlap tests.
        """

        result: list[
            Body2D
        ] = []

        if not self.monitoring:
            return ()

        if not self.enabled:
            return ()

        if not self.collision_enabled:
            return ()

        aabb = (
            self.collision_aabb
        )

        if aabb is None:
            return ()

        x, y, width, height = (
            aabb
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

        for node in candidates:
            if not node.enabled:
                continue

            if not node.collision_enabled:
                continue

            if not node.active_collision_shapes:
                continue

            # ==================================================
            # Area -> Area filtering
            # ==================================================

            if isinstance(
                node,
                Area2D,
            ):
                if not node.monitorable:
                    continue

            # ==================================================
            # Layer / mask
            # ==================================================

            if not self.can_detect(
                node
            ):
                continue

            # ==================================================
            # Narrowphase
            # ==================================================

            if self._shapes_overlap_body(
                node
            ):
                result.append(
                    node
                )

        return tuple(
            result
        )

    # ==============================================================
    # Narrowphase
    # ==============================================================

    def _shapes_overlap_body(
        self,
        body: Body2D,
    ) -> bool:
        """
        Perform exact shape overlap testing.

        Area detection is one-way:

            Area mask -> Body layer

        The other body's mask does not need to detect the Area.
        """

        own_shapes = (
            self.active_collision_shapes
        )

        other_shapes = (
            body.active_collision_shapes
        )

        for own_shape in own_shapes:
            for other_shape in other_shapes:
                if own_shape.overlaps(
                    other_shape
                ):
                    return True

        return False

    # ==============================================================
    # Queries
    # ==============================================================

    @property
    def overlapping_bodies(
        self,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        return tuple(
            self._overlapping_bodies
        )

    def has_overlapping_bodies(
        self,
    ) -> bool:
        return bool(
            self._overlapping_bodies
        )

    def overlaps(
        self,
        body: Body2D,
    ) -> bool:
        """
        Immediately test whether this Area2D overlaps a body.

        Does not modify monitored overlap state.
        """

        return self.overlaps_body_now(
            body
        )

    def overlaps_body_now(
        self,
        body: Body2D,
    ) -> bool:
        """
        Perform an immediate overlap query.
        """

        if body is self:
            return False

        if not self.monitoring:
            return False

        if not self.enabled:
            return False

        if not self.collision_enabled:
            return False

        if not body.enabled:
            return False

        if not body.collision_enabled:
            return False

        if isinstance(
            body,
            Area2D,
        ):
            if not body.monitorable:
                return False

        if not self.can_detect(
            body
        ):
            return False

        return self._shapes_overlap_body(
            body
        )

    # ==============================================================
    # Callback registration
    # ==============================================================

    def connect_body_entered(
        self,
        callback: BodyCallback,
    ) -> None:
        if callback in self._body_entered_callbacks:
            return

        self._body_entered_callbacks.append(
            callback
        )

    def disconnect_body_entered(
        self,
        callback: BodyCallback,
    ) -> None:
        try:
            self._body_entered_callbacks.remove(
                callback
            )

        except ValueError:
            pass

    def connect_body_exited(
        self,
        callback: BodyCallback,
    ) -> None:
        if callback in self._body_exited_callbacks:
            return

        self._body_exited_callbacks.append(
            callback
        )

    def disconnect_body_exited(
        self,
        callback: BodyCallback,
    ) -> None:
        try:
            self._body_exited_callbacks.remove(
                callback
            )

        except ValueError:
            pass

    # ==============================================================
    # Emit
    # ==============================================================

    def _emit_body_entered(
        self,
        body: Body2D,
    ) -> None:
        for callback in tuple(
            self._body_entered_callbacks
        ):
            callback(
                body
            )

    def _emit_body_exited(
        self,
        body: Body2D,
    ) -> None:
        for callback in tuple(
            self._body_exited_callbacks
        ):
            callback(
                body
            )

    # ==============================================================
    # Clear
    # ==============================================================

    def clear_overlaps(
        self,
        *,
        emit_exited: bool = False,
    ) -> None:
        """
        Clear the monitored overlap state.
        """

        if not emit_exited:
            self._overlapping_bodies.clear()
            return

        previous = tuple(
            self._overlapping_bodies
        )

        self._overlapping_bodies.clear()

        for body in previous:
            self._emit_body_exited(
                body
            )