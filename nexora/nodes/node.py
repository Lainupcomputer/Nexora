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
    # Destroy
    # ==============================================================

    def destroy(
        self,
    ) -> None:
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