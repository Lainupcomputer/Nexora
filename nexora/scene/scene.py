from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes.node import Node
from nexora.nodes.ui.controls.text_input import TextInput
from nexora.nodes.ui.ui_root import UIRoot
from nexora.ui import UIInput


class Scene:
    """
    A hierarchical collection of nodes backed by an ECS world.
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        self.name = name

        self.world = World()

        self.root = Node(
            "Root",
            self.world,
        )

        self.ui = UIRoot(
            "UI",
            self.world,
        )

        self.ui_input = UIInput()

    # ==============================================================
    # Nodes
    # ==============================================================

    @property
    def nodes(
        self,
    ) -> tuple[Node, ...]:
        """
        Return the direct children of the scene root.
        """

        return tuple(
            self.root.children
        )


    def create_node(
        self,
        name: str,
        parent: Node | None = None,
        *,
        node_type: type[Node] = Node,
    ) -> Node:
        if parent is None:
            parent = self.root

        if parent.world is not self.world:
            raise ValueError(
                "Parent node does not belong to this scene."
            )

        node = node_type(
            name,
            self.world,
        )

        parent.add_child(
            node
        )

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

        parent.add_child(
            node
        )

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
            node.parent.remove_child(
                node
            )

    def find(
        self,
        name: str,
    ) -> Node | None:
        if self.root.name == name:
            return self.root

        return self.root.find_child(
            name
        )

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        self.root.update_tree(
            delta_time
        )

        self.world.update(
            delta_time
        )

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:
        self.root.fixed_update_tree(
            fixed_delta_time
        )

        self.world.fixed_update(
            fixed_delta_time
        )

    # ==============================================================
    # Render
    # ==============================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        self.world.render(
            interpolation
        )

    def render_nodes(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        self.root.render_tree(
            renderer,
            interpolation,
        )

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        input_manager,
    ) -> None:
        """
        Transfer InputManager state into the scene UI system.

        InputManager stores SDL mouse coordinates with the origin in
        the top-left corner.

        Nexora UI coordinates use the center of the viewport as
        (0, 0), so the mouse position must be converted here.
        """

        # ----------------------------------------------------------
        # Mouse
        # ----------------------------------------------------------

        mouse_x, mouse_y = (
            input_manager.mouse_position
        )

        viewport_width = (
            self.ui.size[0]
        )

        viewport_height = (
            self.ui.size[1]
        )

        ui_mouse_x = (
            mouse_x
            - viewport_width / 2.0
        )

        ui_mouse_y = (
            mouse_y
            - viewport_height / 2.0
        )

        wheel_x, wheel_y = (
            input_manager.wheel
        )

        self.ui_input.update_mouse(
            position=(
                ui_mouse_x,
                ui_mouse_y,
            ),
            down=input_manager.mouse_down(
                "left",
            ),
            pressed=input_manager.mouse_pressed(
                "left",
            ),
            released=input_manager.mouse_released(
                "left",
            ),
            wheel_x=wheel_x,
            wheel_y=wheel_y,
        )

        # ----------------------------------------------------------
        # Keyboard
        # ----------------------------------------------------------

        self.ui_input.update_keyboard(
            keys_down=input_manager.keys_down,
            keys_pressed=input_manager.keys_pressed,
            keys_released=input_manager.keys_released,
        )

        # ----------------------------------------------------------
        # Text
        # ----------------------------------------------------------

        self.ui_input.update_text_input(
            input_manager.text_input,
        )

        # ----------------------------------------------------------
        # UI
        # ----------------------------------------------------------

        self.ui.update_input(
            self.ui_input,
        )

        # ----------------------------------------------------------
        # SDL text input mode
        # ----------------------------------------------------------

        focused_node = (
            self.ui.focused_node
        )

        if isinstance(
            focused_node,
            TextInput,
        ):
            input_manager.start_text_input()

        else:
            input_manager.stop_text_input()

    # ==============================================================
    # Destroy
    # ==============================================================

    def destroy(
        self,
    ) -> None:
        self.root.destroy()
        self.ui.destroy()