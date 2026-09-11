from __future__ import annotations

from nexora.ecs.world import World
from nexora.scene.node import Node


class Scene:
    """A hierarchical collection of nodes backed by an ECS world."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.world = World()
        self.root = Node("Root", self.world)

    @property
    def nodes(self) -> tuple[Node, ...]:
        """Return the direct children of the scene root."""
        return tuple(self.root.children)

    def create_node(
        self,
        name: str,
        parent: Node | None = None,
    ) -> Node:
        if parent is None:
            parent = self.root

        if parent.world is not self.world:
            raise ValueError(
                "Parent node does not belong to this scene."
            )

        node = Node(name, self.world)
        parent.add_child(node)

        return node

    def add_node(
        self,
        node: Node,
        parent: Node | None = None,
    ) -> None:
        if node.world is not self.world:
            raise ValueError(
                "Node does not belong to this scene."
            )

        if node is self.root:
            raise ValueError(
                "The scene root cannot be added as a child."
            )

        if parent is None:
            parent = self.root

        if parent.world is not self.world:
            raise ValueError(
                "Parent node does not belong to this scene."
            )

        parent.add_child(node)

    def remove_node(self, node: Node) -> None:
        if node.world is not self.world:
            raise ValueError(
                "Node does not belong to this scene."
            )

        if node is self.root:
            raise ValueError(
                "The scene root cannot be removed."
            )

        if node.parent is not None:
            node.parent.remove_child(node)

    def find(self, name: str) -> Node | None:
        if self.root.name == name:
            return self.root

        return self.root.find_child(name)

    def update(self, delta_time: float) -> None:
        """Update all ECS systems in this scene."""
        self.world.update(delta_time)

    def fixed_update(self, fixed_delta_time: float) -> None:
        """Run fixed updates for all ECS systems in this scene."""
        self.world.fixed_update(fixed_delta_time)

    def render(self, interpolation: float) -> None:
        """Render all ECS systems in this scene."""
        self.world.render(interpolation)


    def destroy(self) -> None:
        self.root.destroy()