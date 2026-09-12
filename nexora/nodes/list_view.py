from __future__ import annotations

from nexora.nodes.label import Label
from nexora.nodes.scroll_view import ScrollView

class ListView(ScrollView):
    """
    Vertical scrolling list for Nexora UI.

    ```
    ListView builds on ScrollView and automatically arranges
    its child labels vertically.

    Items are ordered from top to bottom.

    Example:

        list_view = scene.ui.create_child(
            "ListView",
            node_type=ListView,
        )

        list_view.size = (
            400.0,
            500.0,
        )

        list_view.set_items(
            [
                "Item 1",
                "Item 2",
                "Item 3",
            ]
        )
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

        # --------------------------------------------------
        # List appearance / layout
        # --------------------------------------------------

        self.item_height: float = 50.0
        self.spacing: float = 0.0

        self.padding_left: float = 15.0
        self.padding_top: float = 15.0
        self.padding_right: float = 15.0
        self.padding_bottom: float = 15.0

        self.text_scale: float = 1.0

        self.text_color = (
            255,
            255,
            255,
            255,
        )

        # --------------------------------------------------
        # Data
        # --------------------------------------------------

        self.items: list[str] = []

        # --------------------------------------------------
        # Internal nodes
        # --------------------------------------------------

        self._item_nodes: list[Label] = []

    # ======================================================
    # Items
    # ======================================================

    def set_items(
        self,
        items: list[str] | tuple[str, ...],
    ) -> None:
        """
        Replace all list items.
        """

        self.items = [
            str(item)
            for item in items
        ]

        self._rebuild_items()

    def add_item(
        self,
        item: str,
    ) -> None:
        """
        Add one item to the end of the list.
        """

        self.items.append(
            str(item)
        )

        self._rebuild_items()

    def remove_item(
        self,
        index: int,
    ) -> None:
        """
        Remove an item by index.
        """

        if (
            index < 0
            or index >= len(self.items)
        ):
            return

        del self.items[index]

        self._rebuild_items()

    def clear(self) -> None:
        """
        Remove all list items.
        """

        self.items.clear()

        self._rebuild_items()

    # ======================================================
    # Item access
    # ======================================================

    def get_item(
        self,
        index: int,
    ) -> str:
        """
        Return an item by index.
        """

        return self.items[index]

    # ======================================================
    # Internal item creation
    # ======================================================

    def _rebuild_items(self) -> None:
        """
        Rebuild all item labels.
        """

        for node in self._item_nodes:
            node.destroy()

        self._item_nodes.clear()

        for index, item in enumerate(
            self.items
        ):
            label = self.create_content_child(
                f"Item{index}",
                node_type=Label,
            )

            label.anchor = (
                0.0,
                0.0,
            )

            label.pivot = (
                0.0,
                0.0,
            )

            label.position = (
                self.padding_left,
                self.padding_top
                + index
                * (
                    self.item_height
                    + self.spacing
                ),
            )

            label.text = item

            label.text_scale = (
                self.text_scale
            )

            label.text_color = (
                self.text_color
            )

            self._item_nodes.append(
                label
            )

        self._update_content_size()

    # ======================================================
    # Layout
    # ======================================================

    def _update_content_size(self) -> None:
        """
        Update the ScrollView content size
        based on the current number of items.
        """

        if not self.items:
            content_height = (
                self.padding_top
                + self.padding_bottom
            )

        else:
            content_height = (
                self.padding_top
                + self.padding_bottom
                + len(self.items)
                * self.item_height
                + max(
                    0,
                    len(self.items) - 1,
                )
                * self.spacing
            )

        content_width = max(
            self.size[0],
            0.0,
        )

        self.set_content_size(
            content_width,
            content_height,
        )

    def _sync_item_layout(self) -> None:
        """
        Recalculate item positions and content size.
        """

        for index, label in enumerate(
            self._item_nodes
        ):
            label.position = (
                self.padding_left,
                self.padding_top
                + index
                * (
                    self.item_height
                    + self.spacing
                ),
            )

            label.text_scale = (
                self.text_scale
            )

            label.text_color = (
                self.text_color
            )

        self._update_content_size()

    # ======================================================
    # Update
    # ======================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        self._sync_item_layout()

        super().update_input(
            ui_input,
        )

    # ======================================================
    # Rendering
    # ======================================================

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._sync_item_layout()

        super().render(
            renderer,
        )

