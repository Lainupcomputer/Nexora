from __future__ import annotations

from nexora.nodes.ui_node import UINode


class UIRoot(UINode):
    """Root node for a scene's UI hierarchy."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.focused_node: UINode | None = None

    def set_viewport_size(
        self,
        width: float,
        height: float,
    ) -> None:
        super().set_viewport_size(width, height)

        self.size = (
            float(width),
            float(height),
        )

    def set_focus(
        self,
        node: UINode | None,
    ) -> None:
        if node is self.focused_node:
            return

        previous = self.focused_node
        self.focused_node = node

        if previous is not None:
            set_focus = getattr(previous, "set_focus", None)

            if set_focus is not None:
                set_focus(False)

        if node is not None:
            set_focus = getattr(node, "set_focus", None)

            if set_focus is not None:
                set_focus(True)

    def _find_focused_nodes(
        self,
        node: UINode,
        result: list[UINode],
    ) -> None:
        for child in node.children:
            if not isinstance(child, UINode):
                continue

            if getattr(child, "focused", False):
                result.append(child)

            self._find_focused_nodes(
                child,
                result,
            )

    def update_input(self, ui_input) -> None:
        if not self.visible or not self.enabled:
            return

        super().update_input(ui_input)

        focused_nodes: list[UINode] = []

        self._find_focused_nodes(
            self,
            focused_nodes,
        )

        if not focused_nodes:
            self.focused_node = None
            return

        focused = focused_nodes[-1]

        for node in focused_nodes:
            if node is not focused:
                set_focus = getattr(node, "set_focus", None)

                if set_focus is not None:
                    set_focus(False)

        self.focused_node = focused