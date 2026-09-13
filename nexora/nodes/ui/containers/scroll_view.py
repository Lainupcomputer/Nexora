from __future__ import annotations

from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.ui_node import UINode


class ScrollView(Panel):
    """
    A vertically scrollable UI container.

    The ScrollView provides a viewport for a larger content area.

    Coordinates:
        Content children use the content area's top-left corner
        as their local layout reference.

    Notes:
        Current clipping is node-based culling. Nodes completely
        outside the viewport are skipped. True pixel/scissor clipping
        is handled separately by the renderer and is not implemented
        here yet.
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

        # ==========================================================
        # Scrolling
        # ==========================================================

        self.scroll_y: float = 0.0
        self.scroll_speed: float = 40.0

        self.content_size: tuple[float, float] = (
            0.0,
            0.0,
        )

        self.on_scroll = None

        # ==========================================================
        # Content
        # ==========================================================

        self.content = self.create_child(
            "Content",
            node_type=UINode,
        )

        self.content.anchor = (
            0.5,
            0.5,
        )

        self.content.pivot = (
            0.5,
            0.5,
        )

        self.content.position = (
            0.0,
            0.0,
        )

        self.content.size = (
            0.0,
            0.0,
        )

        # ==========================================================
        # Internal state
        # ==========================================================

        self._hovered: bool = False

        self._culled_nodes: list[
            UINode
        ] = []

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def max_scroll_y(
        self,
    ) -> float:
        """
        Maximum vertical scroll position.
        """

        visible_height = max(
            float(self.size[1]),
            0.0,
        )

        content_height = max(
            float(self.content_size[1]),
            0.0,
        )

        return max(
            content_height
            - visible_height,
            0.0,
        )

    # ==============================================================
    # Content
    # ==============================================================

    def set_content_size(
        self,
        width: float,
        height: float,
    ) -> None:
        """
        Set the total scrollable content size.
        """

        self.content_size = (
            max(
                float(width),
                0.0,
            ),
            max(
                float(height),
                0.0,
            ),
        )

        self.content.size = (
            self.content_size
        )

        # Resizing the content may reduce the valid scroll range.
        self.set_scroll_y(
            self.scroll_y,
        )

        self._sync_content_layout()

    def create_content_child(
        self,
        name: str,
        node_type: type[UINode] | None = None,
    ) -> UINode:
        """
        Create a node inside the scrollable content.
        """

        return self.content.create_child(
            name,
            node_type=node_type,
        )

    # ==============================================================
    # Scrolling
    # ==============================================================

    def set_scroll_y(
        self,
        value: float,
        *,
        emit: bool = True,
    ) -> bool:
        """
        Set the vertical scroll position.

        Returns True when the scroll position changed.
        """

        old_value = float(
            self.scroll_y
        )

        new_value = max(
            0.0,
            min(
                float(value),
                self.max_scroll_y,
            ),
        )

        if new_value == old_value:
            return False

        self.scroll_y = (
            new_value
        )

        self._sync_content_layout()

        if emit:
            callback = (
                self.on_scroll
            )

            if callback is not None:
                callback(
                    self.scroll_y
                )

        return True

    def scroll_by(
        self,
        amount: float,
    ) -> bool:
        """
        Move the current scroll position.
        """

        return self.set_scroll_y(
            self.scroll_y
            + float(amount),
        )

    def scroll_to_top(
        self,
    ) -> bool:
        return self.set_scroll_y(
            0.0
        )

    def scroll_to_bottom(
        self,
    ) -> bool:
        return self.set_scroll_y(
            self.max_scroll_y
        )

    def _clamp_scroll(
        self,
    ) -> None:
        """
        Clamp without emitting a callback.

        Used internally for layout/render synchronization.
        """

        self.scroll_y = max(
            0.0,
            min(
                float(
                    self.scroll_y
                ),
                self.max_scroll_y,
            ),
        )

    # ==============================================================
    # Layout
    # ==============================================================

    def _sync_content_layout(
        self,
    ) -> None:
        self.content.size = (
            self.content_size
        )

        offset_y = (
            self.content_size[1]
            - self.size[1]
        ) * 0.5

        self.content.position = (
            0.0,
            offset_y
            - self.scroll_y,
        )

    # ==============================================================
    # Viewport
    # ==============================================================

    def _get_viewport_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Return:

            left, top, right, bottom
        """

        x, y = (
            self.calculate_position()
        )

        width, height = (
            self.size
        )

        left = (
            x
            - width
            * self.pivot[0]
        )

        top = (
            y
            - height
            * self.pivot[1]
        )

        return (
            left,
            top,
            left + width,
            top + height,
        )

    def _get_node_rect(
        self,
        node: UINode,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        x, y = (
            node.calculate_position()
        )

        width, height = (
            node.size
        )

        left = (
            x
            - width
            * node.pivot[0]
        )

        top = (
            y
            - height
            * node.pivot[1]
        )

        return (
            left,
            top,
            left + width,
            top + height,
        )

    def _is_inside_viewport(
        self,
        node: UINode,
    ) -> bool:
        """
        Return True when any part of the node intersects the viewport.
        """

        (
            node_left,
            node_top,
            node_right,
            node_bottom,
        ) = self._get_node_rect(
            node
        )

        (
            view_left,
            view_top,
            view_right,
            view_bottom,
        ) = self._get_viewport_rect()

        return not (
            node_right < view_left
            or node_left > view_right
            or node_bottom < view_top
            or node_top > view_bottom
        )

    def _point_inside_viewport(
        self,
        x: float,
        y: float,
    ) -> bool:
        """
        Explicit viewport hit test.

        This is used for input so children cannot react to mouse
        interaction outside the ScrollView rectangle.
        """

        (
            left,
            top,
            right,
            bottom,
        ) = self._get_viewport_rect()

        return (
            left <= x <= right
            and top <= y <= bottom
        )

    # ==============================================================
    # Culling
    # ==============================================================

    def _collect_culled_nodes(
        self,
        node: UINode,
    ) -> None:
        for child in node.children:
            if not isinstance(
                child,
                UINode,
            ):
                continue

            # Respect user-controlled visibility.
            if not child.visible:
                continue

            if not self._is_inside_viewport(
                child
            ):
                self._culled_nodes.append(
                    child
                )

                # Children cannot be visible if their parent
                # is culled.
                continue

            self._collect_culled_nodes(
                child
            )

    def _apply_culling(
        self,
    ) -> None:
        self._culled_nodes.clear()

        self._collect_culled_nodes(
            self.content
        )

        for node in self._culled_nodes:
            node._scroll_view_original_visible = (
                node.visible
            )

            node.visible = False

    def _restore_culling(
        self,
    ) -> None:
        for node in self._culled_nodes:
            original_visible = getattr(
                node,
                "_scroll_view_original_visible",
                True,
            )

            node.visible = (
                original_visible
            )

            if hasattr(
                node,
                "_scroll_view_original_visible",
            ):
                delattr(
                    node,
                    "_scroll_view_original_visible",
                )

        self._culled_nodes.clear()

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        # ----------------------------------------------------------
        # Disabled / hidden
        # ----------------------------------------------------------

        if not self.interactive:
            self._hovered = False
            self.reset_interaction_state()

            # Also clear child interaction state so a button cannot
            # remain hovered/pressed when its ScrollView is disabled.
            self._reset_content_interaction(
                self.content
            )

            return

        # ----------------------------------------------------------
        # Layout
        # ----------------------------------------------------------

        self._clamp_scroll()
        self._sync_content_layout()

        # ----------------------------------------------------------
        # Mouse
        # ----------------------------------------------------------

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self._hovered = (
            self._point_inside_viewport(
                mouse_x,
                mouse_y,
            )
        )

        self.hovered = (
            self._hovered
        )

        # ----------------------------------------------------------
        # Wheel
        # ----------------------------------------------------------

        wheel_y = float(
            getattr(
                ui_input,
                "mouse_wheel_y",
                0.0,
            )
        )

        if (
            self._hovered
            and wheel_y != 0.0
        ):
            self.scroll_by(
                -wheel_y
                * self.scroll_speed
            )

        # ----------------------------------------------------------
        # Child input
        # ----------------------------------------------------------

        self._clamp_scroll()
        self._sync_content_layout()

        if self._hovered:
            self._apply_culling()

            try:
                self.content.update_input(
                    ui_input
                )

            finally:
                self._restore_culling()

        else:
            # Pointer interaction outside the viewport must not
            # remain active in content controls.
            self._clear_content_hover(
                self.content
            )

    def _clear_content_hover(
        self,
        node: UINode,
    ) -> None:
        for child in node.children:
            if not isinstance(
                child,
                UINode,
            ):
                continue

            child.hovered = False

            self._clear_content_hover(
                child
            )

    def _reset_content_interaction(
        self,
        node: UINode,
    ) -> None:
        for child in node.children:
            if not isinstance(
                child,
                UINode,
            ):
                continue

            child.reset_interaction_state()

            self._reset_content_interaction(
                child
            )

    # ==============================================================
    # Rendering
    # ==============================================================

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._clamp_scroll()
        self._sync_content_layout()

        # ----------------------------------------------------------
        # Background
        # ----------------------------------------------------------

        x, y = (
            self.calculate_position()
        )

        renderer.rect(
            x,
            y,
            self.size[0],
            self.size[1],
            color=self._color_to_float(
                self.background
            ),
            radius=self.border_radius,
        )

        # ----------------------------------------------------------
        # Content
        # ----------------------------------------------------------

        self._apply_culling()

        try:
            self.content.render(
                renderer
            )

        finally:
            self._restore_culling()