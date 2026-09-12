from __future__ import annotations

import sdl3

from nexora.nodes.ui_node import UINode


class UIRoot(UINode):
    """
    Root node of Nexora's UI tree.

    Responsibilities:
        - Store the current viewport size.
        - Manage keyboard focus.
        - Handle TAB / SHIFT+TAB focus navigation.
        - Resolve root-level fill / percent sizing.
        - Dispatch UI input.
        - Render the UI tree.
    """

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self._is_ui_root = True

        # ==========================================================
        # Root layout
        # ==========================================================

        self.anchor = (
            0.5,
            0.5,
        )

        self.pivot = (
            0.5,
            0.5,
        )

        self.position = (
            0.0,
            0.0,
        )

        # ==========================================================
        # Focus
        # ==========================================================

        self.focusable = False

        self.focused_node: UINode | None = None

    # ==============================================================
    # Viewport
    # ==============================================================

    def set_viewport_size(
        self,
        width: float,
        height: float,
    ) -> None:
        """
        Set the UI viewport size.

        The root always matches the complete viewport.

        Direct children using:

            width_mode = "fill"
            height_mode = "fill"

        or:

            width_mode = "percent"
            height_mode = "percent"

        are resolved against this size.
        """

        width = max(
            0.0,
            float(width),
        )

        height = max(
            0.0,
            float(height),
        )

        self._viewport_width = width
        self._viewport_height = height

        self.size = (
            width,
            height,
        )

        for child in self.children:
            if not isinstance(
                child,
                UINode,
            ):
                continue

            child.set_viewport_size(
                width,
                height,
            )

            child.apply_resolved_size(
                width,
                height,
            )

    # ==============================================================
    # Root child sizing
    # ==============================================================

    def _resolve_root_children(
        self,
    ) -> None:
        """
        Resolve sizing modes of direct root children.

        This is also performed every frame so changes to width_mode,
        height_mode or percentages become effective immediately.
        """

        width, height = (
            self.size
        )

        for child in self.children:
            if not isinstance(
                child,
                UINode,
            ):
                continue

            child.apply_resolved_size(
                width,
                height,
            )

    # ==============================================================
    # Focus collection
    # ==============================================================

    def _collect_focusable_nodes(
        self,
    ) -> list[UINode]:
        """
        Return focusable nodes in UI tree order.
        """

        result: list[UINode] = []

        def visit(
            node: UINode,
        ) -> None:
            for child in node.children:
                if not isinstance(
                    child,
                    UINode,
                ):
                    continue

                if child.can_focus:
                    result.append(
                        child
                    )

                visit(
                    child
                )

        visit(
            self
        )

        return result

    # ==============================================================
    # Focus management
    # ==============================================================

    def set_focus(
        self,
        node: UINode | None,
    ) -> bool:
        """
        Give keyboard focus to a node.
        """

        if node is None:
            self.clear_focus()
            return True

        if not node.can_focus:
            return False

        if self.focused_node is node:
            return True

        previous = (
            self.focused_node
        )

        self.focused_node = node

        if previous is not None:
            previous._set_focused(
                False
            )

        node._set_focused(
            True
        )

        return True

    def clear_focus(
        self,
    ) -> None:
        """
        Clear the current keyboard focus.
        """

        previous = (
            self.focused_node
        )

        self.focused_node = None

        if previous is not None:
            previous._set_focused(
                False
            )

    def focus_next(
        self,
    ) -> None:
        """
        Move focus to the next focusable node.
        """

        nodes = (
            self._collect_focusable_nodes()
        )

        if not nodes:
            self.clear_focus()
            return

        current = (
            self.focused_node
        )

        if current not in nodes:
            self.set_focus(
                nodes[0]
            )
            return

        index = (
            nodes.index(current)
            + 1
        ) % len(nodes)

        self.set_focus(
            nodes[index]
        )

    def focus_previous(
        self,
    ) -> None:
        """
        Move focus to the previous focusable node.
        """

        nodes = (
            self._collect_focusable_nodes()
        )

        if not nodes:
            self.clear_focus()
            return

        current = (
            self.focused_node
        )

        if current not in nodes:
            self.set_focus(
                nodes[-1]
            )
            return

        index = (
            nodes.index(current)
            - 1
        ) % len(nodes)

        self.set_focus(
            nodes[index]
        )

    # ==============================================================
    # Focus validation
    # ==============================================================

    def _validate_focus(
        self,
    ) -> None:
        """
        Remove focus if the currently focused node can no longer
        receive focus.
        """

        node = (
            self.focused_node
        )

        if node is None:
            return

        if not node.can_focus:
            self.clear_focus()
            return

        # Ensure the node is still part of this UI tree.
        current: UINode | None = node

        while current is not None:
            if current is self:
                return

            parent = current.parent

            if not isinstance(
                parent,
                UINode,
            ):
                break

            current = parent

        self.clear_focus()

    # ==============================================================
    # Keyboard focus navigation
    # ==============================================================

    def _handle_focus_navigation(
        self,
        ui_input,
    ) -> None:
        """
        Handle TAB and SHIFT+TAB.
        """

        if not ui_input.key_pressed(
            sdl3.SDL_SCANCODE_TAB
        ):
            return

        shift_down = (
            ui_input.key_down(
                sdl3.SDL_SCANCODE_LSHIFT
            )
            or
            ui_input.key_down(
                sdl3.SDL_SCANCODE_RSHIFT
            )
        )

        if shift_down:
            self.focus_previous()

        else:
            self.focus_next()

    # ==============================================================
    # Mouse focus
    # ==============================================================

    def _find_focusable_at_point(
        self,
        node: UINode,
        x: float,
        y: float,
    ) -> UINode | None:
        """
        Find the deepest focusable node under the pointer.

        Children are checked in reverse order so later children are
        treated as being visually on top.
        """

        for child in reversed(
            node.children
        ):
            if not isinstance(
                child,
                UINode,
            ):
                continue

            if not child.visible:
                continue

            result = (
                self._find_focusable_at_point(
                    child,
                    x,
                    y,
                )
            )

            if result is not None:
                return result

            if (
                child.can_focus
                and child.contains_point(
                    x,
                    y,
                )
            ):
                return child

        return None

    def _handle_mouse_focus(
        self,
        ui_input,
    ) -> None:
        """
        Assign focus when the user clicks a focusable control.

        Clicking outside all focusable controls clears focus.
        """

        if not ui_input.mouse_left_pressed:
            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        node = (
            self._find_focusable_at_point(
                self,
                mouse_x,
                mouse_y,
            )
        )

        if node is None:
            self.clear_focus()
            return

        self.set_focus(
            node
        )

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        """
        Update the complete UI tree.
        """

        # Root-level responsive sizing must happen before hit testing.
        self._resolve_root_children()

        self._validate_focus()

        # Mouse focus first so a clicked control receives focus
        # during the same frame.
        self._handle_mouse_focus(
            ui_input
        )

        self._handle_focus_navigation(
            ui_input
        )

        # Let children process their own input.
        for child in self.children:
            if isinstance(
                child,
                UINode,
            ):
                child.update_input(
                    ui_input
                )

        self._validate_focus()

    # ==============================================================
    # Rendering
    # ==============================================================

    def render(
        self,
        renderer,
    ) -> None:
        """
        Render the complete UI tree.
        """

        if not self.visible:
            return

        # Keep layout current even when render occurs without an input
        # update before it.
        self._resolve_root_children()

        for child in self.children:
            if isinstance(
                child,
                UINode,
            ):
                child.render(
                    renderer
                )