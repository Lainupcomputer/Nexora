from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.ui.output.label import Label
from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.containers.scroll_view import ScrollView


class ListView(ScrollView):
    """
    Focusable vertical scrolling list.

    Keyboard:
        Up / Down
            Move selection.

        Home / End
            Select first / last item.

        PageUp / PageDown
            Move selection by approximately one visible page.

        Enter / Space
            Activate the selected item.

    Mouse:
        Click an item to select it.

        Mouse wheel scrolling is inherited from ScrollView.
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
        # Focus
        # ==========================================================

        self.focusable = True

        # ==========================================================
        # Layout
        # ==========================================================

        self.item_height: float = 50.0
        self.spacing: float = 0.0

        self.padding_left: float = 15.0
        self.padding_top: float = 15.0
        self.padding_right: float = 15.0
        self.padding_bottom: float = 15.0

        self.text_padding_left: float = 10.0

        self.text_scale: float = 1.0

        # ==========================================================
        # Data
        # ==========================================================

        self.items: list[str] = []

        self.selected_index: int = -1
        self.hovered_index: int = -1

        # ==========================================================
        # Appearance
        # ==========================================================

        self.item_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            32,
            34,
            37,
            255,
        )

        self.item_hover_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            45,
            48,
            53,
            255,
        )

        self.item_selected_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            42,
            70,
            105,
            255,
        )

        self.item_selected_hover_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            52,
            84,
            125,
            255,
        )

        self.focus_border_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
            80,
            140,
            220,
            255,
        )

        self.normal_border_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
            70,
            72,
            76,
            255,
        )

        self.item_border_radius: float = 4.0

        # ==========================================================
        # Callbacks
        # ==========================================================

        self.on_change: (
            Callable[[int, str | None], None]
            | None
        ) = None

        self.on_activate: (
            Callable[[int, str], None]
            | None
        ) = None

        # ==========================================================
        # Internal nodes
        # ==========================================================

        self._item_nodes: list[Panel] = []
        self._item_labels: list[Label] = []

        self._sync_focus_visuals()

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def selected_item(
        self,
    ) -> str | None:
        """
        Return the selected item.
        """

        if not (
            0
            <= self.selected_index
            < len(self.items)
        ):
            return None

        return self.items[
            self.selected_index
        ]

    @property
    def item_step(
        self,
    ) -> float:
        """
        Distance between two item starts.
        """

        return (
            self.item_height
            + self.spacing
        )

    # ==============================================================
    # Focus
    # ==============================================================

    def on_focus(self) -> None:
        self._sync_focus_visuals()

    def on_blur(self) -> None:
        self.hovered_index = -1

        self._sync_focus_visuals()
        self._sync_item_visuals()

    def _sync_focus_visuals(
        self,
    ) -> None:
        """
        Draw a visible border while focused.
        """

        if self.focused:
            self.border_color = (
                self.focus_border_color
            )

            self.border_width = 2.0

        else:
            self.border_color = (
                self.normal_border_color
            )

            self.border_width = 1.0

    # ==============================================================
    # Items
    # ==============================================================

    def set_items(
        self,
        items: list[str]
        | tuple[str, ...],
    ) -> None:
        """
        Replace all list items.
        """

        self.items = [
            str(item)
            for item in items
        ]

        if not self.items:
            self.selected_index = -1

        elif (
            self.selected_index
            >= len(self.items)
        ):
            self.selected_index = (
                len(self.items) - 1
            )

        self.hovered_index = -1

        self._rebuild_items()

    def add_item(
        self,
        item: str,
    ) -> None:
        """
        Add an item.
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

        if not (
            0
            <= index
            < len(self.items)
        ):
            return

        del self.items[index]

        if not self.items:
            self.selected_index = -1

        elif (
            self.selected_index
            >= len(self.items)
        ):
            self.selected_index = (
                len(self.items) - 1
            )

        elif (
            index
            < self.selected_index
        ):
            self.selected_index -= 1

        self.hovered_index = -1

        self._rebuild_items()

    def clear(
        self,
    ) -> None:
        """
        Remove all items.
        """

        self.items.clear()

        self.selected_index = -1
        self.hovered_index = -1

        self._rebuild_items()

    def get_item(
        self,
        index: int,
    ) -> str:
        """
        Return an item by index.
        """

        return self.items[index]

    # ==============================================================
    # Selection
    # ==============================================================

    def set_selected_index(
        self,
        index: int,
        *,
        emit: bool = True,
        ensure_visible: bool = True,
    ) -> None:
        """
        Select an item.
        """

        if not self.items:
            self.selected_index = -1
            return

        index = max(
            0,
            min(
                int(index),
                len(self.items) - 1,
            ),
        )

        changed = (
            index
            != self.selected_index
        )

        self.selected_index = index

        if ensure_visible:
            self.ensure_item_visible(
                index
            )

        self._sync_item_visuals()

        if (
            changed
            and emit
        ):
            callback = self.on_change

            if callback is not None:
                callback(
                    self.selected_index,
                    self.selected_item,
                )

    def select_next(
        self,
    ) -> None:
        """
        Select the next item.
        """

        if not self.items:
            return

        if self.selected_index < 0:
            index = 0

        else:
            index = min(
                self.selected_index + 1,
                len(self.items) - 1,
            )

        self.set_selected_index(
            index
        )

    def select_previous(
        self,
    ) -> None:
        """
        Select the previous item.
        """

        if not self.items:
            return

        if self.selected_index < 0:
            index = (
                len(self.items) - 1
            )

        else:
            index = max(
                self.selected_index - 1,
                0,
            )

        self.set_selected_index(
            index
        )

    def select_first(
        self,
    ) -> None:
        if not self.items:
            return

        self.set_selected_index(
            0
        )

    def select_last(
        self,
    ) -> None:
        if not self.items:
            return

        self.set_selected_index(
            len(self.items) - 1
        )

    # ==============================================================
    # Activation
    # ==============================================================

    def activate_selected(
        self,
    ) -> None:
        """
        Activate the currently selected item.
        """

        if not (
            0
            <= self.selected_index
            < len(self.items)
        ):
            return

        callback = self.on_activate

        if callback is not None:
            callback(
                self.selected_index,
                self.items[
                    self.selected_index
                ],
            )

    # ==============================================================
    # Item creation
    # ==============================================================

    def _rebuild_items(
        self,
    ) -> None:
        """
        Rebuild all item rows.
        """

        for node in self._item_nodes:
            node.destroy()

        self._item_nodes.clear()
        self._item_labels.clear()

        for index, item in enumerate(
            self.items
        ):
            # ------------------------------------------------------
            # Row
            # ------------------------------------------------------

            row = self.create_content_child(
                f"Item{index}",
                node_type=Panel,
            )

            row.anchor = (
                0.0,
                0.0,
            )

            row.pivot = (
                0.0,
                0.0,
            )

            row.border_width = 0.0

            row.border_radius = (
                self.item_border_radius
            )

            # ------------------------------------------------------
            # Label
            # ------------------------------------------------------

            label = row.create_child(
                "Label",
                node_type=Label,
            )

            label.anchor = (
                0.0,
                0.5,
            )

            label.pivot = (
                0.0,
                0.5,
            )

            label.position = (
                self.text_padding_left,
                0.0,
            )

            label.text = item

            label.scale = (
                self.text_scale
            )

            self._item_nodes.append(
                row
            )

            self._item_labels.append(
                label
            )

        self._sync_item_layout()
        self._sync_item_visuals()

    # ==============================================================
    # Content size
    # ==============================================================

    def _update_content_size(
        self,
    ) -> None:
        """
        Update scrollable content size.
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

    # ==============================================================
    # Layout
    # ==============================================================

    def _sync_item_layout(
        self,
    ) -> None:
        """
        Synchronize row and label layout.
        """

        row_width = max(
            self.size[0]
            - self.padding_left
            - self.padding_right,
            0.0,
        )

        for index, row in enumerate(
            self._item_nodes
        ):
            # ------------------------------------------------------
            # Row
            # ------------------------------------------------------

            row.size = (
                row_width,
                self.item_height,
            )

            row.anchor = (
                0.0,
                0.0,
            )

            row.pivot = (
                0.0,
                0.0,
            )

            # Same positioning principle as Dropdown option panels.
            row.position = (
                self.padding_left
                + row_width / 2.0,

                self.padding_top
                + self.item_height / 2.0
                + index
                * self.item_step,
            )

            # ------------------------------------------------------
            # Label
            # ------------------------------------------------------

            label = self._item_labels[
                index
            ]

            label.text = (
                self.items[index]
            )

            label.scale = (
                self.text_scale
            )

            label.anchor = (
                0.0,
                0.5,
            )

            label.pivot = (
                0.0,
                0.5,
            )

            label.position = (
                self.text_padding_left,
                0.0,
            )

        self._update_content_size()

    # ==============================================================
    # Item visuals
    # ==============================================================

    def _sync_item_visuals(
        self,
    ) -> None:
        """
        Synchronize row colors.
        """

        for index, row in enumerate(
            self._item_nodes
        ):
            selected = (
                index
                == self.selected_index
            )

            hovered = (
                index
                == self.hovered_index
            )

            if selected and hovered:
                row.background = (
                    self.item_selected_hover_background
                )

            elif selected:
                row.background = (
                    self.item_selected_background
                )

            elif hovered:
                row.background = (
                    self.item_hover_background
                )

            else:
                row.background = (
                    self.item_background
                )

    # ==============================================================
    # Keep selection visible
    # ==============================================================

    def ensure_item_visible(
        self,
        index: int,
    ) -> None:
        """
        Scroll enough to make an item fully visible.
        """

        if not (
            0
            <= index
            < len(self.items)
        ):
            return

        item_top = (
            self.padding_top
            + index
            * self.item_step
        )

        item_bottom = (
            item_top
            + self.item_height
        )

        visible_top = (
            self.scroll_y
        )

        visible_bottom = (
            self.scroll_y
            + self.size[1]
        )

        if item_top < visible_top:
            self.set_scroll_y(
                item_top
            )

        elif item_bottom > visible_bottom:
            self.set_scroll_y(
                item_bottom
                - self.size[1]
            )

        self._sync_content_layout()

    # ==============================================================
    # Item hit testing
    # ==============================================================

    def _item_contains_point(
        self,
        row: Panel,
        x: float,
        y: float,
    ) -> bool:
        """
        Check whether a point lies inside the full visible row.

        ListView rows are positioned like Dropdown option panels:
        the row position represents the visual center.

        We therefore calculate the visible rectangle explicitly
        instead of using generic UINode.contains_point().
        """

        row_x, row_y = (
            row.calculate_position()
        )

        width, height = (
            row.size
        )

        left = (
            row_x
            - width / 2.0
        )

        top = (
            row_y
            - height / 2.0
        )

        right = (
            row_x
            + width / 2.0
        )

        bottom = (
            row_y
            + height / 2.0
        )

        return (
            left <= x <= right
            and
            top <= y <= bottom
        )

    def _find_item_at_point(
        self,
        x: float,
        y: float,
    ) -> int:
        """
        Return the visible item under the mouse.

        Returns -1 if there is no item under the pointer.
        """

        if not self.contains_point(
            x,
            y,
        ):
            return -1

        for index, row in enumerate(
            self._item_nodes
        ):
            if not self._is_inside_viewport(
                row
            ):
                continue

            if self._item_contains_point(
                row,
                x,
                y,
            ):
                return index

        return -1

    # ==============================================================
    # Page navigation
    # ==============================================================

    def _move_page(
        self,
        direction: int,
    ) -> None:
        """
        Move approximately one visible page.
        """

        if not self.items:
            return

        step = max(
            self.item_step,
            1.0,
        )

        visible_items = max(
            1,
            int(
                self.size[1]
                // step
            )
            - 1,
        )

        if self.selected_index < 0:
            if direction > 0:
                index = 0

            else:
                index = (
                    len(self.items) - 1
                )

        else:
            index = (
                self.selected_index
                + visible_items
                * direction
            )

        self.set_selected_index(
            index
        )

    # ==============================================================
    # Keyboard
    # ==============================================================

    def _handle_keyboard(
        self,
        ui_input,
    ) -> None:
        """
        Process ListView keyboard navigation.
        """

        if not self.focused:
            return

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_UP
        ):
            self.select_previous()
            return

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_DOWN
        ):
            self.select_next()
            return

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_HOME
        ):
            self.select_first()
            return

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_END
        ):
            self.select_last()
            return

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_PAGEUP
        ):
            self._move_page(
                -1
            )
            return

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_PAGEDOWN
        ):
            self._move_page(
                1
            )
            return

        if (
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_RETURN
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_KP_ENTER
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_SPACE
            )
        ):
            self.activate_selected()

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        """
        Process scrolling, mouse selection and keyboard navigation.
        """

        self._sync_item_layout()

        # ----------------------------------------------------------
        # ScrollView
        # ----------------------------------------------------------

        super().update_input(
            ui_input
        )

        if not self.interactive:
            self.hovered_index = -1

            self._sync_item_visuals()

            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        # ----------------------------------------------------------
        # Hover
        # ----------------------------------------------------------

        self.hovered_index = (
            self._find_item_at_point(
                mouse_x,
                mouse_y,
            )
        )

        # ----------------------------------------------------------
        # Mouse selection
        # ----------------------------------------------------------

        if (
            ui_input.mouse_left_pressed
            and self.hovered_index >= 0
        ):
            self.set_selected_index(
                self.hovered_index
            )

        # ----------------------------------------------------------
        # Keyboard
        # ----------------------------------------------------------

        self._handle_keyboard(
            ui_input
        )

        # ----------------------------------------------------------
        # Visuals
        # ----------------------------------------------------------

        self._sync_item_visuals()
        self._sync_focus_visuals()

    # ==============================================================
    # Rendering
    # ==============================================================

    def render(
        self,
        renderer,
    ) -> None:
        """
        Render the ListView.
        """

        if not self.visible:
            return

        self._sync_item_layout()
        self._sync_item_visuals()
        self._sync_focus_visuals()

        super().render(
            renderer
        )