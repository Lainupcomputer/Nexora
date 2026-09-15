from __future__ import annotations

import math

from typing import TYPE_CHECKING

from nexora.ecs.component import Transform
from nexora.ecs.entity import Entity


if TYPE_CHECKING:
    from nexora.ecs.world import World


class Node:
    """
    Hierarchical scene node backed by an ECS entity.

    Nodes provide:

        - parent / child hierarchy
        - hierarchical transforms
        - update lifecycle
        - fixed update lifecycle
        - render lifecycle
    """

    def __init__(
        self,
        name: str,
        world: World,
    ) -> None:
        self.name = name
        self.world = world

        # ======================================================
        # ECS
        # ======================================================

        self.entity: Entity = (
            world.create_entity()
        )

        self.transform = (
            world.add_component(
                self.entity,
                Transform(),
            )
        )

        # ======================================================
        # Hierarchy
        # ======================================================

        self.parent: Node | None = None

        self.children: list[
            Node
        ] = []

        # ======================================================
        # State
        # ======================================================

        self.enabled: bool = True
        self.visible: bool = True

        # ======================================================
        # Signals
        # ======================================================
        #
        # Incoming connections are tracked so destroying a Node
        # automatically disconnects callbacks owned by it.
        # Signals created through create_signal() are tracked as
        # owned signals and are cleared during destruction.

        self._signal_connections: set = set()
        self._owned_signals: set = set()

        # ======================================================
        # Tweens
        # ======================================================
        # Runtime tweens can use a Node as their owner. Tracking
        # them here allows Node.destroy() to stop them immediately.

        self._owned_tweens: set = set()

        # ======================================================
        # Timers
        # ======================================================
        # Runtime timers can use a Node as owner. Destroying the
        # owner cancels them before the ECS entity disappears.

        self._owned_timers: set = set()

        # ======================================================
        # Coroutine tasks
        # ======================================================
        # Generator tasks can use a Node as owner. They are cancelled
        # before the ECS entity is destroyed so no suspended routine can
        # resume against a dead Node.

        self._owned_tasks: set = set()

    # ==============================================================
    # World transform
    # ==============================================================

    @property
    def world_position(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        x = self.transform.x
        y = self.transform.y

        if self.parent is None:
            return (
                x,
                y,
            )

        parent_x, parent_y = (
            self.parent.world_position
        )

        angle = math.radians(
            self.parent.world_rotation
        )

        cos_angle = math.cos(
            angle
        )

        sin_angle = math.sin(
            angle
        )

        rotated_x = (
            x * cos_angle
            - y * sin_angle
        )

        rotated_y = (
            x * sin_angle
            + y * cos_angle
        )

        parent_scale_x, parent_scale_y = (
            self.parent.world_scale
        )

        return (
            parent_x
            + rotated_x
            * parent_scale_x,

            parent_y
            + rotated_y
            * parent_scale_y,
        )

    @property
    def world_rotation(
        self,
    ) -> float:
        if self.parent is None:
            return (
                self.transform.rotation
            )

        return (
            self.parent.world_rotation
            + self.transform.rotation
        )

    @property
    def world_scale(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        if self.parent is None:
            return (
                self.transform.scale_x,
                self.transform.scale_y,
            )

        parent_scale_x, parent_scale_y = (
            self.parent.world_scale
        )

        return (
            parent_scale_x
            * self.transform.scale_x,

            parent_scale_y
            * self.transform.scale_y,
        )

    @property
    def world_transform(
        self,
    ) -> Transform:
        x, y = (
            self.world_position
        )

        scale_x, scale_y = (
            self.world_scale
        )

        return Transform(
            x=x,
            y=y,
            rotation=self.world_rotation,
            scale_x=scale_x,
            scale_y=scale_y,
        )

    # ==============================================================
    # Lifecycle hooks
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Per-frame node update.

        Override in subclasses.
        """

        pass

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:
        """
        Fixed timestep update.

        Override in subclasses.
        """

        pass

    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        """
        Render this node.

        Override in subclasses.
        """

        pass

    # ==============================================================
    # Tree lifecycle
    # ==============================================================

    def update_tree(
        self,
        delta_time: float,
    ) -> None:
        """
        Update this node and all enabled descendants.
        """

        if not self.enabled:
            return

        self.update(
            delta_time
        )

        for child in tuple(
            self.children
        ):
            child.update_tree(
                delta_time
            )

    def fixed_update_tree(
        self,
        fixed_delta_time: float,
    ) -> None:
        """
        Fixed-update this node and all enabled descendants.
        """

        if not self.enabled:
            return

        self.fixed_update(
            fixed_delta_time
        )

        for child in tuple(
            self.children
        ):
            child.fixed_update_tree(
                fixed_delta_time
            )

    def render_tree(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        """
        Render this node and all visible descendants.
        """

        if not self.visible:
            return

        self.render(
            renderer,
            interpolation,
        )

        for child in tuple(
            self.children
        ):
            child.render_tree(
                renderer,
                interpolation,
            )

    # ==============================================================
    # Children
    # ==============================================================

    def add_child(
        self,
        child: Node,
    ) -> None:
        if child is self:
            raise ValueError(
                "A node cannot be its own child."
            )

        if child.world is not self.world:
            raise ValueError(
                "Child node belongs to a different world."
            )

        # Prevent cycles.
        current: Node | None = self

        while current is not None:
            if current is child:
                raise ValueError(
                    "Cannot create a cyclic node hierarchy."
                )

            current = current.parent

        if child.parent is self:
            return

        if child.parent is not None:
            child.parent.remove_child(
                child
            )

        child.parent = self

        self.children.append(
            child
        )

    def remove_child(
        self,
        child: Node,
    ) -> None:
        if child not in self.children:
            return

        self.children.remove(
            child
        )

        child.parent = None

    def find_child(
        self,
        name: str,
    ) -> Node | None:
        for child in self.children:
            if child.name == name:
                return child

            result = (
                child.find_child(
                    name
                )
            )

            if result is not None:
                return result

        return None

    # ==============================================================
    # Tree traversal
    # ==============================================================

    @property
    def tree_root(
        self,
    ) -> Node:
        """
        Return the root node of the current node tree.
        """

        node = self

        while node.parent is not None:
            node = node.parent

        return node


    def iter_tree(
        self,
        *,
        include_self: bool = True,
    ):
        """
        Iterate over this node and all descendants.

        Traversal order is depth-first.
        """

        if include_self:
            yield self

        for child in tuple(
            self.children
        ):
            yield from child.iter_tree(
                include_self=True
            )


    def iter_ancestors(
        self,
    ):
        """
        Iterate from the direct parent up to the tree root.
        """

        node = self.parent

        while node is not None:
            yield node
            node = node.parent


    def is_descendant_of(
        self,
        node: Node,
    ) -> bool:
        """
        Return True when this node is below `node`.
        """

        current = self.parent

        while current is not None:
            if current is node:
                return True

            current = current.parent

        return False

    # ==============================================================
    # Signals
    # ==============================================================

    def create_signal(
        self,
        name: str,
    ):
        """
        Create a Signal owned by this Node.

        Owned signals are cleared automatically when the Node is
        destroyed.
        """

        from nexora.signals import Signal

        return Signal(
            name,
            owner=self,
        )

    def _track_signal_connection(
        self,
        connection,
    ) -> None:
        self._signal_connections.add(
            connection
        )

    def _untrack_signal_connection(
        self,
        connection,
    ) -> None:
        self._signal_connections.discard(
            connection
        )

    def _track_owned_signal(
        self,
        signal,
    ) -> None:
        self._owned_signals.add(
            signal
        )

    def _disconnect_signals(
        self,
    ) -> None:
        # Disconnect listeners first. A connection may remove itself
        # from this set while disconnecting, so iterate over a copy.
        for connection in tuple(
            self._signal_connections
        ):
            connection.disconnect()

        self._signal_connections.clear()

        # Then clear signals emitted by this Node.
        for signal in tuple(
            self._owned_signals
        ):
            signal.clear()

        self._owned_signals.clear()


    # ==============================================================
    # Tweens
    # ==============================================================

    def _track_tween(
        self,
        tween,
    ) -> None:
        self._owned_tweens.add(
            tween
        )

    def _untrack_tween(
        self,
        tween,
    ) -> None:
        self._owned_tweens.discard(
            tween
        )

    def _cancel_tweens(
        self,
    ) -> None:
        for tween in tuple(
            self._owned_tweens
        ):
            stop = getattr(
                tween,
                "stop",
                None,
            )

            if stop is not None:
                stop()

        self._owned_tweens.clear()

    # ==============================================================
    # Timers
    # ==============================================================

    def _track_timer(
        self,
        timer,
    ) -> None:
        self._owned_timers.add(
            timer
        )

    def _untrack_timer(
        self,
        timer,
    ) -> None:
        self._owned_timers.discard(
            timer
        )

    def _cancel_timers(
        self,
    ) -> None:
        for timer in tuple(
            self._owned_timers
        ):
            cancel = getattr(
                timer,
                "cancel",
                None,
            )

            if cancel is not None:
                cancel()

        self._owned_timers.clear()

    # ==============================================================
    # Coroutine tasks
    # ==============================================================

    def _track_task(
        self,
        task,
    ) -> None:
        self._owned_tasks.add(
            task
        )

    def _untrack_task(
        self,
        task,
    ) -> None:
        self._owned_tasks.discard(
            task
        )

    def _cancel_tasks(
        self,
    ) -> None:
        for task in tuple(
            self._owned_tasks
        ):
            cancel = getattr(
                task,
                "cancel",
                None,
            )

            if cancel is not None:
                cancel()

        self._owned_tasks.clear()

    # ==============================================================
    # Destroy
    # ==============================================================

    def destroy(
        self,
    ) -> None:
        self._cancel_tasks()
        self._cancel_timers()
        self._cancel_tweens()
        self._disconnect_signals()

        for child in tuple(
            self.children
        ):
            child.destroy()

        self.children.clear()

        if self.parent is not None:
            self.parent.remove_child(
                self
            )

        if self.world.is_alive(
            self.entity
        ):
            self.world.destroy_entity(
                self.entity
            )