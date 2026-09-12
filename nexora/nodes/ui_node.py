from __future__ import annotations

from nexora.nodes.node import Node


class UINode(Node):
    """
    Base node for Nexora's UI system.

    UI coordinates use the same coordinate system as the renderer:
        (0, 0) = viewport center

    Anchors are normalized viewport coordinates:
        (0.0, 0.0) = top-left
        (0.5, 0.5) = center
        (1.0, 1.0) = bottom-right

    `position` is an offset from the resolved anchor.
    """

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(name, world)

        self.position: tuple[float, float] = (0.0, 0.0)
        self.size: tuple[float, float] = (0.0, 0.0)

        self.anchor: tuple[float, float] = (0.5, 0.5)
        self.pivot: tuple[float, float] = (0.5, 0.5)

        self.visible: bool = True
        self.enabled: bool = True

        self._viewport_width = 0.0
        self._viewport_height = 0.0

    def set_viewport_size(
        self,
        width: float,
        height: float,
    ) -> None:
        """
        Set the viewport size used for UI layout calculations.
        """

        self._viewport_width = float(width)
        self._viewport_height = float(height)

    @property
    def rect(self) -> tuple[float, float, float, float]:
        """
        Return the UI rectangle.

        Returns:
            (x, y, width, height)
        """

        x, y = self.calculate_position()

        return (
            x,
            y,
            self.size[0],
            self.size[1],
        )

    def contains_point(
            self,
            x: float,
            y: float,
        ) -> bool:
            """
            Check whether a point lies inside this UI element.

            The point and UI element use the renderer's coordinate system:
                (0, 0) = viewport center
                +X = right
                +Y = down

            Returns:
                True if the point is inside the UI element.
            """

            rect_x, rect_y, width, height = self.rect

            left = (
                rect_x
                - width * self.pivot[0]
            )

            top = (
                rect_y
                - height * self.pivot[1]
            )

            right = left + width
            bottom = top + height

            return (
                left <= x <= right
                and
                top <= y <= bottom
            )

    def calculate_position(
        self,
        viewport_width: float | None = None,
        viewport_height: float | None = None,
    ) -> tuple[float, float]:
        """
        Calculate the renderer position of this UI element.

        Root UI nodes use their anchor relative to the viewport.

        Child UI nodes use their anchor relative to their parent UI node.
        """

        if viewport_width is None:
            viewport_width = self._viewport_width

        if viewport_height is None:
            viewport_height = self._viewport_height

        if isinstance(self.parent, UINode):
            parent_x, parent_y = self.parent.calculate_position(
                viewport_width,
                viewport_height,
            )

            parent_width, parent_height = self.parent.size

            anchor_x = (
                (self.anchor[0] - 0.5)
                * parent_width
            )

            anchor_y = (
                (self.anchor[1] - 0.5)
                * parent_height
            )

            return (
                parent_x
                + anchor_x
                + self.position[0],
                parent_y
                + anchor_y
                + self.position[1],
            )

        anchor_x = (
            (self.anchor[0] - 0.5)
            * viewport_width
        )

        anchor_y = (
            (self.anchor[1] - 0.5)
            * viewport_height
        )

        return (
            anchor_x + self.position[0],
            anchor_y + self.position[1],
        )

    def set_viewport_size(
        self,
        width: float,
        height: float,
    ) -> None:
        self._viewport_width = float(width)
        self._viewport_height = float(height)

        for child in self.children:
            if isinstance(child, UINode):
                child.set_viewport_size(
                    width,
                    height,
                )

    def create_child(
        self,
        name: str,
        node_type: type[UINode] | None = None,
    ) -> UINode:
        """
        Create and attach a child UI node.
        """

        if node_type is None:
            node_type = UINode

        child = node_type(
            name,
            self.world,
        )

        self.add_child(child)

        child.set_viewport_size(
            self._viewport_width,
            self._viewport_height,
        )

        return child

    def update_input(
        self,
        ui_input,
    ) -> None:
        """
        Dispatch input to UI children.

        UI nodes that handle input can override this method.
        """

        if not self.visible:
            return

        for child in self.children:
            if isinstance(child, UINode):
                child.update_input(ui_input)

    def render(self, renderer) -> None:
        """
        Render this UI node and its children.
        """

        if not self.visible:
            return

        for child in self.children:
            if isinstance(child, UINode):
                child.render(renderer)

