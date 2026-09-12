from __future__ import annotations

from nexora.nodes.panel import Panel
from nexora.nodes.ui_node import UINode


class ScrollView(Panel):
    """
    A vertically scrollable UI container.

    The ScrollView provides a viewport for a larger content area.
    Mouse wheel input moves the content vertically.

    Content children are created through `create_content_child()` and
    use the content area's top-left corner as their local origin.

    Attributes:
        scroll_y:
            Current vertical scroll position.

        scroll_speed:
            Amount of content movement per mouse-wheel unit.

        content_size:
            Size of the scrollable content area.

        on_scroll:
            Optional callback receiving the current scroll position.
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

        # --------------------------------------------------------------
        # Scrolling
        # --------------------------------------------------------------

        self.scroll_y: float = 0.0
        self.scroll_speed: float = 40.0

        self.content_size: tuple[float, float] = (
            0.0,
            0.0,
        )

        self.on_scroll = None

        # --------------------------------------------------------------
        # Content
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # Internal state
        # --------------------------------------------------------------

        self._hovered = False
        self._last_scroll_y = 0.0

        self._culled_nodes: list[UINode] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def max_scroll_y(self) -> float:
        """
        Return the maximum vertical scroll position.
        """

        visible_height = max(
            self.size[1],
            0.0,
        )

        content_height = max(
            self.content_size[1],
            0.0,
        )

        return max(
            content_height - visible_height,
            0.0,
        )

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def set_content_size(
        self,
        width: float,
        height: float,
    ) -> None:
        """
        Set the size of the scrollable content area.
        """

        self.content_size = (
            max(float(width), 0.0),
            max(float(height), 0.0),
        )

        self.content.size = self.content_size

        self._clamp_scroll()

    def create_content_child(
        self,
        name: str,
        node_type: type[UINode] | None = None,
    ) -> UINode:
        """
        Create a UI node inside the scrollable content area.
        """

        return self.content.create_child(
            name,
            node_type=node_type,
        )

    # ------------------------------------------------------------------
    # Scrolling
    # ------------------------------------------------------------------

    def set_scroll_y(
        self,
        value: float,
        *,
        emit: bool = True,
    ) -> None:
        """
        Set the vertical scroll position.
        """

        old_value = self.scroll_y

        self.scroll_y = float(value)

        self._clamp_scroll()

        if (
            emit
            and self.scroll_y != old_value
        ):
            callback = self.on_scroll

            if callback is not None:
                callback(self.scroll_y)

    def scroll_by(
        self,
        amount: float,
    ) -> None:
        """
        Move the content vertically.
        """

        self.set_scroll_y(
            self.scroll_y + float(amount),
        )

    def scroll_to_top(self) -> None:
        """Scroll to the top of the content."""

        self.set_scroll_y(0.0)

    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the content."""

        self.set_scroll_y(
            self.max_scroll_y,
        )

    def _clamp_scroll(self) -> None:
        self.scroll_y = max(
            0.0,
            min(
                self.scroll_y,
                self.max_scroll_y,
            ),
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _sync_content_layout(self) -> None:
        self.content.size = self.content_size

        offset_y = (
            self.content_size[1] - self.size[1]
        ) / 2.0

        self.content.position = (
            0.0,
            offset_y - self.scroll_y,
        )
            
    # ------------------------------------------------------------------
    # Viewport
    # ------------------------------------------------------------------

    def _get_viewport_rect(
        self,
    ) -> tuple[float, float, float, float]:
        """
        Return the visible viewport rectangle.

        Returns:
            (left, top, right, bottom)
        """

        view_x, view_y = self.calculate_position()

        width = self.size[0]
        height = self.size[1]

        left = (
            view_x
            - width * self.pivot[0]
        )

        top = (
            view_y
            - height * self.pivot[1]
        )

        right = left + width
        bottom = top + height

        return (
            left,
            top,
            right,
            bottom,
        )

    def _get_node_rect(
        self,
        node: UINode,
    ) -> tuple[float, float, float, float]:
        """
        Return a UI node's world-space rectangle.
        """

        x, y = node.calculate_position()

        width = node.size[0]
        height = node.size[1]

        left = (
            x
            - width * node.pivot[0]
        )

        top = (
            y
            - height * node.pivot[1]
        )

        right = left + width
        bottom = top + height

        return (
            left,
            top,
            right,
            bottom,
        )

    def _is_inside_viewport(
        self,
        node: UINode,
    ) -> bool:
        """
        Check whether a node intersects the ScrollView viewport.
        """

        (
            node_left,
            node_top,
            node_right,
            node_bottom,
        ) = self._get_node_rect(node)

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

    # ------------------------------------------------------------------
    # Culling
    # ------------------------------------------------------------------

    def _collect_culled_nodes(
        self,
        node: UINode,
    ) -> None:
        """
        Collect nodes that are outside the visible viewport.

        The original `visible` state is never modified permanently.
        """

        for child in node.children:
            if not isinstance(child, UINode):
                continue

            if not child.visible:
                continue

            if not self._is_inside_viewport(child):
                self._culled_nodes.append(child)
                continue

            self._collect_culled_nodes(child)

    def _apply_culling(self) -> None:
        """
        Temporarily hide nodes outside the viewport.
        """

        self._culled_nodes.clear()

        self._collect_culled_nodes(
            self.content,
        )

        for node in self._culled_nodes:
            node._scroll_view_visible = node.visible
            node.visible = False

    def _restore_culling(self) -> None:
        """
        Restore the original visibility of culled nodes.
        """

        for node in self._culled_nodes:
            original_visible = getattr(
                node,
                "_scroll_view_visible",
                True,
            )

            node.visible = original_visible

            if hasattr(
                node,
                "_scroll_view_visible",
            ):
                del node._scroll_view_visible

        self._culled_nodes.clear()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def update_input(
        self,
        ui_input,
    ) -> None:
        if (
            not self.visible
            or not self.enabled
        ):
            self._hovered = False
            return

        # --------------------------------------------------------------
        # Layout
        # --------------------------------------------------------------

        self._clamp_scroll()
        self._sync_content_layout()

        # --------------------------------------------------------------
        # Mouse
        # --------------------------------------------------------------

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self._hovered = self.contains_point(
            mouse_x,
            mouse_y,
        )

        # --------------------------------------------------------------
        # Mouse wheel
        # --------------------------------------------------------------

        wheel_y = getattr(
            ui_input,
            "mouse_wheel_y",
            0.0,
        )

        if (
            self._hovered
            and wheel_y != 0.0
        ):
            self.scroll_by(
                -wheel_y * self.scroll_speed,
            )

        # --------------------------------------------------------------
        # Update layout after scrolling
        # --------------------------------------------------------------

        self._clamp_scroll()
        self._sync_content_layout()

        # --------------------------------------------------------------
        # Child input
        # --------------------------------------------------------------

        self._apply_culling()

        try:
            self.content.update_input(
                ui_input,
            )
        finally:
            self._restore_culling()

        # --------------------------------------------------------------
        # Callback
        # --------------------------------------------------------------

        if self.scroll_y != self._last_scroll_y:
            callback = self.on_scroll

            if callback is not None:
                callback(self.scroll_y)

            self._last_scroll_y = self.scroll_y

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._clamp_scroll()
        self._sync_content_layout()

        # --------------------------------------------------------------
        # Background
        # --------------------------------------------------------------

        x, y = self.calculate_position()

        renderer.rect(
            x,
            y,
            self.size[0],
            self.size[1],
            color=self._color_to_float(
                self.background,
            ),
            radius=self.border_radius,
        )

        # --------------------------------------------------------------
        # Content
        # --------------------------------------------------------------

        self._apply_culling()

        try:
            self.content.render(
                renderer,
            )
        finally:
            self._restore_culling()