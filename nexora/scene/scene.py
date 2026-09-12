from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes.node import Node
from nexora.nodes.ui_root import UIRoot
from nexora.ui import UIInput


class Scene:
    """A hierarchical collection of nodes backed by an ECS world."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.world = World()

        self.root = Node("Root", self.world)
        self.ui = UIRoot("UI", self.world)
        self.ui_input = UIInput()

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

    def remove_node(
        self,
        node: Node,
    ) -> None:
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

    def find(
        self,
        name: str,
    ) -> Node | None:
        if self.root.name == name:
            return self.root

        return self.root.find_child(name)

    def update(
        self,
        delta_time: float,
    ) -> None:
        self.world.update(delta_time)

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:
        self.world.fixed_update(fixed_delta_time)

    def render(
        self,
        interpolation: float,
    ) -> None:
        self.world.render(interpolation)

    def destroy(self) -> None:
        self.root.destroy()
        self.ui.destroy()

    def update_input(
        self,
        input_manager,
    ) -> None:
        wheel_x, wheel_y = input_manager.wheel

        self.ui_input.update_mouse(
            position=input_manager.mouse_position,
            down=input_manager.mouse_down("left"),
            pressed=input_manager.mouse_pressed("left"),
            released=input_manager.mouse_released("left"),
            wheel_x=wheel_x,
            wheel_y=wheel_y,
        )

        self.ui_input.update_keyboard(
            keys_down=input_manager.keys_down,
            keys_pressed=input_manager.keys_pressed,
            keys_released=input_manager.keys_released,
        )

        self.ui_input.update_text_input(
            input_manager.text_input,
        )

        self.ui.update_input(
            self.ui_input,
        )

        focused_node = self.ui.focused_node

        if focused_node is not None:
            input_manager.start_text_input()
        else:
            input_manager.stop_text_input()