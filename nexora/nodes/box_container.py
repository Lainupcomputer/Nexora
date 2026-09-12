from __future__ import annotations

from nexora.nodes.ui_node import UINode


class BoxContainer(UINode):
    """
    Base class for automatic box layouts.

    Layout pipeline:

        measure()
            Determine desired sizes recursively.

        arrange()
            Assign final sizes and child positions.

    Supported features:

        - vertical / horizontal layout
        - spacing
        - padding
        - start / center / end / stretch alignment
        - minimum sizes
        - proportional grow
        - fixed / fill / percent / content sizing
        - fit_content
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
        # Layout
        # ==========================================================

        self.spacing: float = 10.0

        self.padding_left: float = 0.0
        self.padding_top: float = 0.0
        self.padding_right: float = 0.0
        self.padding_bottom: float = 0.0

        # Cross-axis alignment:
        #
        #   start
        #   center
        #   end
        #   stretch
        self.alignment: str = "start"

        # vertical / horizontal
        self.orientation: str = "vertical"

        # Size this container from its children.
        self.fit_content: bool = False

    # ==============================================================
    # Helpers
    # ==============================================================

    def _layout_children(
        self,
    ) -> list[UINode]:
        """
        Return visible direct UI children participating in layout.
        """

        return [
            child
            for child in self.children
            if (
                isinstance(
                    child,
                    UINode,
                )
                and child.visible
            )
        ]

    @staticmethod
    def _grow_total(
        children: list[UINode],
    ) -> float:
        """
        Return total grow weight.
        """

        return sum(
            child.grow
            for child in children
        )

    def _validate_alignment(
        self,
    ) -> None:
        if self.alignment not in (
            "start",
            "center",
            "end",
            "stretch",
        ):
            raise ValueError(
                "BoxContainer alignment must be "
                "'start', 'center', 'end' or 'stretch'."
            )

    # ==============================================================
    # Measure
    # ==============================================================

    def measure(
        self,
        available_width: float | None = None,
        available_height: float | None = None,
    ) -> tuple[float, float]:
        """
        Measure this container and all visible children.

        Measurement runs recursively from parent into children and
        returns the desired size before arrange() assigns final sizes.
        """

        self._validate_alignment()

        children = (
            self._layout_children()
        )

        # ----------------------------------------------------------
        # Resolve own normal size
        # ----------------------------------------------------------

        base_width, base_height = (
            super().measure(
                available_width,
                available_height,
            )
        )

        inner_available_width = max(
            0.0,
            base_width
            - self.padding_left
            - self.padding_right,
        )

        inner_available_height = max(
            0.0,
            base_height
            - self.padding_top
            - self.padding_bottom,
        )

        # ----------------------------------------------------------
        # Measure children recursively
        # ----------------------------------------------------------

        child_sizes: list[
            tuple[
                UINode,
                float,
                float,
            ]
        ] = []

        for child in children:
            child_width, child_height = (
                child.measure(
                    inner_available_width,
                    inner_available_height,
                )
            )

            child_sizes.append(
                (
                    child,
                    child_width,
                    child_height,
                )
            )

        spacing_total = (
            max(
                0,
                len(children) - 1,
            )
            * self.spacing
        )

        # ----------------------------------------------------------
        # Calculate required content size
        # ----------------------------------------------------------

        if self.orientation == "vertical":
            content_width = max(
                (
                    width
                    for _, width, _
                    in child_sizes
                ),
                default=0.0,
            )

            content_height = sum(
                height
                for _, _, height
                in child_sizes
            )

            content_height += (
                spacing_total
            )

        elif self.orientation == "horizontal":
            content_width = sum(
                width
                for _, width, _
                in child_sizes
            )

            content_width += (
                spacing_total
            )

            content_height = max(
                (
                    height
                    for _, _, height
                    in child_sizes
                ),
                default=0.0,
            )

        else:
            raise ValueError(
                "BoxContainer orientation must be "
                "'vertical' or 'horizontal'."
            )

        desired_width = (
            content_width
            + self.padding_left
            + self.padding_right
        )

        desired_height = (
            content_height
            + self.padding_top
            + self.padding_bottom
        )

        # ----------------------------------------------------------
        # Content sizing
        # ----------------------------------------------------------

        if (
            self.fit_content
            or self.width_mode == "content"
        ):
            base_width = max(
                desired_width,
                self.minimum_width,
            )

        if (
            self.fit_content
            or self.height_mode == "content"
        ):
            base_height = max(
                desired_height,
                self.minimum_height,
            )

        self._desired_size = (
            base_width,
            base_height,
        )

        return self._desired_size

    # ==============================================================
    # Arrange
    # ==============================================================

    def arrange(
        self,
        width: float,
        height: float,
    ) -> None:
        """
        Assign final container size and arrange its children.
        """

        self._validate_alignment()

        super().arrange(
            width,
            height,
        )

        children = (
            self._layout_children()
        )

        if self.orientation == "vertical":
            self._arrange_vertical(
                children
            )

        elif self.orientation == "horizontal":
            self._arrange_horizontal(
                children
            )

        else:
            raise ValueError(
                "BoxContainer orientation must be "
                "'vertical' or 'horizontal'."
            )

    # ==============================================================
    # Vertical arrangement
    # ==============================================================

    def _arrange_vertical(
        self,
        children: list[UINode],
    ) -> None:
        """
        Arrange children from top to bottom.
        """

        inner_width = max(
            0.0,
            self.size[0]
            - self.padding_left
            - self.padding_right,
        )

        inner_height = max(
            0.0,
            self.size[1]
            - self.padding_top
            - self.padding_bottom,
        )

        spacing_total = (
            max(
                0,
                len(children) - 1,
            )
            * self.spacing
        )

        # ----------------------------------------------------------
        # Determine fixed/base height
        # ----------------------------------------------------------

        base_height = 0.0

        for child in children:
            _, desired_height = (
                child.desired_size
            )

            if child.grow > 0.0:
                base_height += (
                    child.minimum_height
                )

            else:
                base_height += max(
                    desired_height,
                    child.minimum_height,
                )

        # ----------------------------------------------------------
        # Remaining space for grow children
        # ----------------------------------------------------------

        grow_space = max(
            0.0,
            inner_height
            - spacing_total
            - base_height,
        )

        total_grow = (
            self._grow_total(
                children
            )
        )

        cursor_y = (
            self.padding_top
        )

        # ----------------------------------------------------------
        # Arrange every child
        # ----------------------------------------------------------

        for child in children:
            desired_width, desired_height = (
                child.desired_size
            )

            width = max(
                desired_width,
                child.minimum_width,
            )

            # ------------------------------------------------------
            # Main axis
            # ------------------------------------------------------

            if child.grow > 0.0:
                height = (
                    child.minimum_height
                )

                if total_grow > 0.0:
                    height += (
                        grow_space
                        * (
                            child.grow
                            / total_grow
                        )
                    )

            else:
                height = max(
                    desired_height,
                    child.minimum_height,
                )

            # ------------------------------------------------------
            # Cross-axis alignment
            # ------------------------------------------------------

            if self.alignment == "start":
                x = (
                    self.padding_left
                    + width / 2.0
                )

            elif self.alignment == "center":
                x = (
                    self.size[0]
                    / 2.0
                )

            elif self.alignment == "end":
                x = (
                    self.size[0]
                    - self.padding_right
                    - width / 2.0
                )

            else:
                # stretch
                if child.layout_stretch:
                    width = max(
                        inner_width,
                        child.minimum_width,
                    )

                x = (
                    self.padding_left
                    + width / 2.0
                )

            # ------------------------------------------------------
            # Position
            # ------------------------------------------------------

            child.anchor = (
                0.0,
                0.0,
            )

            child.pivot = (
                0.5,
                0.5,
            )

            child.position = (
                x,
                cursor_y
                + height / 2.0,
            )

            # ------------------------------------------------------
            # Recursively arrange child
            # ------------------------------------------------------

            child.arrange(
                width,
                height,
            )

            cursor_y += (
                height
                + self.spacing
            )

    # ==============================================================
    # Horizontal arrangement
    # ==============================================================

    def _arrange_horizontal(
        self,
        children: list[UINode],
    ) -> None:
        """
        Arrange children from left to right.
        """

        inner_width = max(
            0.0,
            self.size[0]
            - self.padding_left
            - self.padding_right,
        )

        inner_height = max(
            0.0,
            self.size[1]
            - self.padding_top
            - self.padding_bottom,
        )

        spacing_total = (
            max(
                0,
                len(children) - 1,
            )
            * self.spacing
        )

        # ----------------------------------------------------------
        # Determine fixed/base width
        # ----------------------------------------------------------

        base_width = 0.0

        for child in children:
            desired_width, _ = (
                child.desired_size
            )

            if child.grow > 0.0:
                base_width += (
                    child.minimum_width
                )

            else:
                base_width += max(
                    desired_width,
                    child.minimum_width,
                )

        # ----------------------------------------------------------
        # Remaining grow space
        # ----------------------------------------------------------

        grow_space = max(
            0.0,
            inner_width
            - spacing_total
            - base_width,
        )

        total_grow = (
            self._grow_total(
                children
            )
        )

        cursor_x = (
            self.padding_left
        )

        # ----------------------------------------------------------
        # Arrange every child
        # ----------------------------------------------------------

        for child in children:
            desired_width, desired_height = (
                child.desired_size
            )

            height = max(
                desired_height,
                child.minimum_height,
            )

            # ------------------------------------------------------
            # Main axis
            # ------------------------------------------------------

            if child.grow > 0.0:
                width = (
                    child.minimum_width
                )

                if total_grow > 0.0:
                    width += (
                        grow_space
                        * (
                            child.grow
                            / total_grow
                        )
                    )

            else:
                width = max(
                    desired_width,
                    child.minimum_width,
                )

            # ------------------------------------------------------
            # Cross-axis alignment
            # ------------------------------------------------------

            if self.alignment == "start":
                y = (
                    self.padding_top
                    + height / 2.0
                )

            elif self.alignment == "center":
                y = (
                    self.size[1]
                    / 2.0
                )

            elif self.alignment == "end":
                y = (
                    self.size[1]
                    - self.padding_bottom
                    - height / 2.0
                )

            else:
                # stretch
                if child.layout_stretch:
                    height = max(
                        inner_height,
                        child.minimum_height,
                    )

                y = (
                    self.padding_top
                    + height / 2.0
                )

            # ------------------------------------------------------
            # Position
            # ------------------------------------------------------

            child.anchor = (
                0.0,
                0.0,
            )

            child.pivot = (
                0.5,
                0.5,
            )

            child.position = (
                cursor_x
                + width / 2.0,
                y,
            )

            # ------------------------------------------------------
            # Recursively arrange child
            # ------------------------------------------------------

            child.arrange(
                width,
                height,
            )

            cursor_x += (
                width
                + self.spacing
            )

    # ==============================================================
    # Full local layout pass
    # ==============================================================

    def update_layout(
        self,
    ) -> None:
        """
        Measure and arrange this complete container subtree.
        """

        available_width = (
            self.size[0]
        )

        available_height = (
            self.size[1]
        )

        desired_width, desired_height = (
            self.measure(
                available_width,
                available_height,
            )
        )

        # ----------------------------------------------------------
        # Determine final own size
        # ----------------------------------------------------------

        if (
            self.fit_content
            or self.width_mode == "content"
        ):
            final_width = (
                desired_width
            )

        else:
            final_width = (
                self.size[0]
            )

        if (
            self.fit_content
            or self.height_mode == "content"
        ):
            final_height = (
                desired_height
            )

        else:
            final_height = (
                self.size[1]
            )

        self.arrange(
            final_width,
            final_height,
        )

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        self.update_layout()

        super().update_input(
            ui_input
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

        self.update_layout()

        super().render(
            renderer
        )


class VBoxContainer(BoxContainer):
    """
    Arrange children vertically.
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

        self.orientation = "vertical"


class HBoxContainer(BoxContainer):
    """
    Arrange children horizontally.
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

        self.orientation = "horizontal"