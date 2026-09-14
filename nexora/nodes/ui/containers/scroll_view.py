from __future__ import annotations

from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.ui_node import UINode


class ScrollView(Panel):
    """
    A vertically scrollable UI container.

    The ScrollView provides a viewport for a larger content area.

    Rendering uses the renderer clip stack, so partially visible
    elements are clipped pixel-perfectly instead of being hidden
    completely.

    Content children are created through create_content_child().
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

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def max_scroll_y(
        self,
    ) -> float:
        """
        Return the maximum vertical scroll position.
        """

        visible_height = max(
            float(
                self.size[1]
            ),
            0.0,
        )

        content_height = max(
            float(
                self.content_size[1]
            ),
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
        Set the total size of the scrollable content area.
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

        self._clamp_scroll()
        self._sync_content_layout()

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

        Returns True if the value changed.
        """

        old_value = float(
            self.scroll_y
        )

        self.scroll_y = float(
            value
        )

        self._clamp_scroll()
        self._sync_content_layout()

        if (
            emit
            and self.scroll_y != old_value
        ):
            callback = self.on_scroll

            if callback is not None:
                callback(
                    self.scroll_y
                )

        return (
            self.scroll_y
            != old_value
        )

    def scroll_by(
        self,
        amount: float,
    ) -> bool:
        """
        Scroll by a relative amount.
        """

        return self.set_scroll_y(
            self.scroll_y
            + float(amount)
        )

    def scroll_to_top(
        self,
    ) -> bool:
        """
        Scroll to the top.
        """

        return self.set_scroll_y(
            0.0
        )

    def scroll_to_bottom(
        self,
    ) -> bool:
        """
        Scroll to the bottom.
        """

        return self.set_scroll_y(
            self.max_scroll_y
        )

    def _clamp_scroll(
        self,
    ) -> None:
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
        """
        Position the content node according to scroll_y.
        """

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
        Return the visible viewport rectangle as:

            left,
            top,
            right,
            bottom

        Coordinates use Nexora's centered screen space.
        """

        x, y = (
            self.calculate_position()
        )

        width = float(
            self.size[0]
        )

        height = float(
            self.size[1]
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

        right = (
            left
            + width
        )

        bottom = (
            top
            + height
        )

        return (
            left,
            top,
            right,
            bottom,
        )

    def _get_clip_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Return the viewport in renderer clip format:

            x,
            y,
            width,
            height
        """

        (
            left,
            top,
            right,
            bottom,
        ) = self._get_viewport_rect()

        return (
            left,
            top,
            max(
                right - left,
                0.0,
            ),
            max(
                bottom - top,
                0.0,
            ),
        )

    def _point_inside_viewport(
        self,
        x: float,
        y: float,
    ) -> bool:
        """
        Return True if a point is inside the ScrollView viewport.
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
    # Interaction reset
    # ==============================================================

    def _reset_child_interaction(
        self,
        node: UINode,
    ) -> None:
        """
        Clear hover/pressed state recursively.

        This prevents controls inside the ScrollView from remaining
        hovered or pressed when the pointer leaves the viewport.
        """

        for child in node.children:
            if not isinstance(
                child,
                UINode,
            ):
                continue

            child.reset_interaction_state()

            self._reset_child_interaction(
                child
            )

    def _clear_child_hover(
        self,
        node: UINode,
    ) -> None:
        """
        Clear only hover state recursively.
        """

        for child in node.children:
            if not isinstance(
                child,
                UINode,
            ):
                continue

            child.hovered = False

            self._clear_child_hover(
                child
            )

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

            self._reset_child_interaction(
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
        # Mouse wheel
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
        # Update content position after scrolling
        # ----------------------------------------------------------

        self._clamp_scroll()
        self._sync_content_layout()

        # ----------------------------------------------------------
        # Child input
        # ----------------------------------------------------------
        #
        # Children only receive pointer input while the pointer is
        # inside the ScrollView viewport.
        #
        # This is the input equivalent of GPU clipping.
        # ----------------------------------------------------------

        if self._hovered:
            self.content.update_input(
                ui_input
            )

        else:
            self._clear_child_hover(
                self.content
            )

    # ==============================================================
    # Render
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
        # GPU clip
        # ----------------------------------------------------------
        #
        # The ScrollView background is intentionally rendered
        # BEFORE enabling the clip.
        #
        # Only the actual content is clipped.
        # ----------------------------------------------------------

        (
            clip_x,
            clip_y,
            clip_width,
            clip_height,
        ) = self._get_clip_rect()

        renderer.push_clip_rect(
            clip_x,
            clip_y,
            clip_width,
            clip_height,
        )

        try:
            self.content.render(
                renderer
            )

        finally:
            renderer.pop_clip_rect()