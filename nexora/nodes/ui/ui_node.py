from __future__ import annotations

from nexora.nodes.node import Node


class UINode(Node):
    """
    Base node for Nexora's UI system.

    Coordinates:
        (0, 0) = viewport center

    Anchors:
        (0.0, 0.0) = top-left
        (0.5, 0.5) = center
        (1.0, 1.0) = bottom-right
    """

    VALID_SIZE_MODES = (
        "fixed",
        "fill",
        "percent",
        "content",
    )

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

        self.position: tuple[float, float] = (
            0.0,
            0.0,
        )

        self.size: tuple[float, float] = (
            0.0,
            0.0,
        )

        self.anchor: tuple[float, float] = (
            0.5,
            0.5,
        )

        self.pivot: tuple[float, float] = (
            0.5,
            0.5,
        )

        # ----------------------------------------------------------
        # Size modes
        # ----------------------------------------------------------

        self.width_mode: str = "fixed"
        self.height_mode: str = "fixed"

        self.width_percent: float = 1.0
        self.height_percent: float = 1.0

        # ----------------------------------------------------------
        # Layout properties
        # ----------------------------------------------------------

        self.min_size: tuple[float, float] = (
            0.0,
            0.0,
        )

        self.layout_grow: float = 0.0
        self.layout_stretch: bool = True

        # ----------------------------------------------------------
        # Measured / desired size
        # ----------------------------------------------------------

        self._desired_size: tuple[float, float] = (
            0.0,
            0.0,
        )

        # ==========================================================
        # General state
        # ==========================================================

        self.visible: bool = True
        self.enabled: bool = True

        # ==========================================================
        # Interaction state
        # ==========================================================

        self.hovered: bool = False
        self.pressed: bool = False

        # ==========================================================
        # Focus
        # ==========================================================

        self.focusable: bool = False
        self.focused: bool = False

        # ==========================================================
        # Viewport
        # ==========================================================

        self._viewport_width: float = 0.0
        self._viewport_height: float = 0.0

    # ==============================================================
    # Size helpers
    # ==============================================================

    @staticmethod
    def _validate_size_mode(
        mode: str,
    ) -> str:
        mode = str(mode).lower()

        if mode not in UINode.VALID_SIZE_MODES:
            raise ValueError(
                "UI size mode must be "
                "'fixed', 'fill', 'percent' or 'content'."
            )

        return mode

    @property
    def minimum_width(self) -> float:
        return max(
            0.0,
            float(self.min_size[0]),
        )

    @property
    def minimum_height(self) -> float:
        return max(
            0.0,
            float(self.min_size[1]),
        )

    @property
    def grow(self) -> float:
        return max(
            0.0,
            float(self.layout_grow),
        )

    @property
    def desired_size(
        self,
    ) -> tuple[float, float]:
        return self._desired_size

    # ==============================================================
    # Measure
    # ==============================================================

    def measure(
        self,
        available_width: float | None = None,
        available_height: float | None = None,
    ) -> tuple[float, float]:
        """
        Determine the desired size of this node.

        This does not position the node.
        """

        width, height = self.size

        width_mode = self._validate_size_mode(
            self.width_mode
        )

        height_mode = self._validate_size_mode(
            self.height_mode
        )

        # ----------------------------------------------------------
        # Width
        # ----------------------------------------------------------

        if available_width is not None:
            available_width = max(
                0.0,
                float(available_width),
            )

            if width_mode == "fill":
                width = available_width

            elif width_mode == "percent":
                width = (
                    available_width
                    * max(
                        0.0,
                        self.width_percent,
                    )
                )

        # ----------------------------------------------------------
        # Height
        # ----------------------------------------------------------

        if available_height is not None:
            available_height = max(
                0.0,
                float(available_height),
            )

            if height_mode == "fill":
                height = available_height

            elif height_mode == "percent":
                height = (
                    available_height
                    * max(
                        0.0,
                        self.height_percent,
                    )
                )

        width = max(
            float(width),
            self.minimum_width,
        )

        height = max(
            float(height),
            self.minimum_height,
        )

        self._desired_size = (
            width,
            height,
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
        Assign the final size of this node.
        """

        self.size = (
            max(
                float(width),
                self.minimum_width,
            ),
            max(
                float(height),
                self.minimum_height,
            ),
        )

    # ==============================================================
    # Legacy size resolution helpers
    # ==============================================================

    def resolve_size(
        self,
        available_width: float | None = None,
        available_height: float | None = None,
    ) -> tuple[float, float]:
        return self.measure(
            available_width,
            available_height,
        )

    def apply_resolved_size(
        self,
        available_width: float | None = None,
        available_height: float | None = None,
    ) -> None:
        width, height = self.measure(
            available_width,
            available_height,
        )

        self.arrange(
            width,
            height,
        )

    # ==============================================================
    # Interaction
    # ==============================================================

    @property
    def interactive(self) -> bool:
        return (
            self.visible
            and self.enabled
        )

    def update_hover(
        self,
        x: float,
        y: float,
    ) -> bool:
        if not self.interactive:
            self.hovered = False
            return False

        self.hovered = self.contains_point(
            x,
            y,
        )

        return self.hovered

    def set_pressed(
        self,
        pressed: bool,
    ) -> None:
        if not self.interactive:
            pressed = False

        pressed = bool(pressed)

        if self.pressed == pressed:
            return

        self.pressed = pressed

        if pressed:
            self.on_press()
        else:
            self.on_release()

    def reset_interaction_state(self) -> None:
        was_pressed = self.pressed

        self.hovered = False
        self.pressed = False

        if was_pressed:
            self.on_release()

    def on_press(self) -> None:
        pass

    def on_release(self) -> None:
        pass

    # ==============================================================
    # Focus
    # ==============================================================

    @property
    def can_focus(self) -> bool:
        return (
            self.focusable
            and self.interactive
        )

    @property
    def ui_root(self):
        node: Node | None = self

        while node is not None:
            if getattr(
                node,
                "_is_ui_root",
                False,
            ):
                return node

            node = node.parent

        return None

    def focus(self) -> bool:
        if not self.can_focus:
            return False

        root = self.ui_root

        if root is None:
            return False

        return root.set_focus(
            self
        )

    def blur(self) -> None:
        root = self.ui_root

        if (
            root is not None
            and root.focused_node is self
        ):
            root.clear_focus()
            return

        if self.focused:
            self._set_focused(
                False
            )

    def _set_focused(
        self,
        focused: bool,
    ) -> None:
        focused = bool(focused)

        if self.focused == focused:
            return

        self.focused = focused

        if focused:
            self.on_focus()
        else:
            self.on_blur()

    def on_focus(self) -> None:
        pass

    def on_blur(self) -> None:
        self.set_pressed(
            False
        )

    # ==============================================================
    # Viewport
    # ==============================================================

    def set_viewport_size(
        self,
        width: float,
        height: float,
    ) -> None:
        self._viewport_width = float(width)
        self._viewport_height = float(height)

        for child in self.children:
            if isinstance(
                child,
                UINode,
            ):
                child.set_viewport_size(
                    width,
                    height,
                )

    # ==============================================================
    # Position
    # ==============================================================

    @property
    def rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        x, y = self.calculate_position()

        return (
            x,
            y,
            self.size[0],
            self.size[1],
        )

    def calculate_position(
        self,
        viewport_width: float | None = None,
        viewport_height: float | None = None,
    ) -> tuple[float, float]:
        if viewport_width is None:
            viewport_width = (
                self._viewport_width
            )

        if viewport_height is None:
            viewport_height = (
                self._viewport_height
            )

        if isinstance(
            self.parent,
            UINode,
        ):
            parent_x, parent_y = (
                self.parent.calculate_position(
                    viewport_width,
                    viewport_height,
                )
            )

            parent_width, parent_height = (
                self.parent.size
            )

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
            anchor_x
            + self.position[0],

            anchor_y
            + self.position[1],
        )

    # ==============================================================
    # Hit testing
    # ==============================================================

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        rect_x, rect_y, width, height = (
            self.rect
        )

        left = (
            rect_x
            - width
            * self.pivot[0]
        )

        top = (
            rect_y
            - height
            * self.pivot[1]
        )

        right = left + width
        bottom = top + height

        return (
            left <= x <= right
            and
            top <= y <= bottom
        )

    # ==============================================================
    # Children
    # ==============================================================

    def create_child(
        self,
        name: str,
        node_type: type[UINode] | None = None,
    ) -> UINode:
        if node_type is None:
            node_type = UINode

        child = node_type(
            name,
            self.world,
        )

        self.add_child(
            child
        )

        child.set_viewport_size(
            self._viewport_width,
            self._viewport_height,
        )

        return child

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        if not self.interactive:
            self.reset_interaction_state()
            return

        for child in self.children:
            if isinstance(
                child,
                UINode,
            ):
                child.update_input(
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

        for child in self.children:
            if isinstance(
                child,
                UINode,
            ):
                child.render(
                    renderer
                )