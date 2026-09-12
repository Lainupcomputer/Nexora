from __future__ import annotations

from nexora.nodes.panel import Panel
from nexora.nodes.label import Label


class Dropdown(Panel):
    """
    A dropdown selection UI component.

    The dropdown displays one selected option and can be opened
    to display a list of available options.

    Options are strings and are selected by index.

    Attributes:
        options:
            Available option strings.

        selected_index:
            Index of the currently selected option.

        opened:
            Whether the option list is currently visible.

        on_change:
            Callback called with the selected index and value.
    """

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(name, world)

        # --------------------------------------------------
        # Dropdown state
        # --------------------------------------------------

        self.options: list[str] = []
        self.selected_index: int = -1
        self.opened: bool = False

        self.on_change = None

        # --------------------------------------------------
        # Appearance
        # --------------------------------------------------

        self.background = (
            32,
            34,
            37,
            255,
        )

        self.hover_background = (
            45,
            48,
            53,
            255,
        )

        self.option_background = (
            32,
            34,
            37,
            255,
        )

        self.option_hover_background = (
            55,
            58,
            63,
            255,
        )

        self.text_color = (
            255,
            255,
            255,
            255,
        )

        self.disabled_color = (
            120,
            120,
            120,
            255,
        )

        self.option_height: float = 40.0
        self.text_scale: float = 1.0

        # --------------------------------------------------
        # Internal nodes
        # --------------------------------------------------

        self._label = self.create_child(
            "Label",
            node_type=Label,
        )

        self._label.anchor = (
            0.0,
            0.5,
        )

        self._label.pivot = (
            0.0,
            0.5,
        )

        self._label.position = (
            15.0,
            0.0,
        )

        self._label.text_scale = self.text_scale
        self._label.text_color = self.text_color

        self._arrow = self.create_child(
            "Arrow",
            node_type=Label,
        )

        self._arrow.anchor = (
            1.0,
            0.5,
        )

        self._arrow.pivot = (
            1.0,
            0.5,
        )

        self._arrow.position = (
            -15.0,
            0.0,
        )

        self._arrow.text = "▼"
        self._arrow.text_scale = self.text_scale
        self._arrow.text_color = self.text_color

        self._option_nodes: list[Panel] = []
        self._option_labels: list[Label] = []

        self._hovered = False
        self._pressed = False

        self._sync_label()

    # --------------------------------------------------
    # Properties
    # --------------------------------------------------

    @property
    def selected_value(self) -> str | None:
        """Return the currently selected value."""

        if (
            self.selected_index < 0
            or self.selected_index >= len(self.options)
        ):
            return None

        return self.options[self.selected_index]

    # --------------------------------------------------
    # Options
    # --------------------------------------------------

    def set_options(
        self,
        options: list[str] | tuple[str, ...],
    ) -> None:
        """Replace all dropdown options."""

        self.options = [
            str(option)
            for option in options
        ]

        if not self.options:
            self.selected_index = -1

        elif self.selected_index < 0:
            self.selected_index = 0

        elif self.selected_index >= len(self.options):
            self.selected_index = len(self.options) - 1

        self._rebuild_options()
        self._sync_label()

    def add_option(
        self,
        option: str,
    ) -> None:
        """Add one option to the dropdown."""

        self.options.append(str(option))

        if self.selected_index < 0:
            self.selected_index = 0

        self._rebuild_options()
        self._sync_label()

    def remove_option(
        self,
        index: int,
    ) -> None:
        """Remove an option by index."""

        if (
            index < 0
            or index >= len(self.options)
        ):
            return

        del self.options[index]

        if not self.options:
            self.selected_index = -1

        elif self.selected_index >= len(self.options):
            self.selected_index = len(self.options) - 1

        elif index < self.selected_index:
            self.selected_index -= 1

        elif index == self.selected_index:
            self.selected_index = min(
                self.selected_index,
                len(self.options) - 1,
            )

        self._rebuild_options()
        self._sync_label()

    def clear_options(self) -> None:
        """Remove all options."""

        self.options.clear()
        self.selected_index = -1
        self.opened = False

        self._rebuild_options()
        self._sync_label()

    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def set_selected_index(
        self,
        index: int,
        *,
        emit: bool = True,
    ) -> None:
        """Select an option by index."""

        if not self.options:
            self.selected_index = -1
            self._sync_label()
            return

        index = max(
            0,
            min(index, len(self.options) - 1),
        )

        if index == self.selected_index:
            self._sync_label()
            return

        self.selected_index = index
        self._sync_label()

        if emit:
            callback = self.on_change

            if callback is not None:
                callback(
                    self.selected_index,
                    self.selected_value,
                )

    # --------------------------------------------------
    # Internal option creation
    # --------------------------------------------------

    def _rebuild_options(self) -> None:
        """Rebuild the visual option list."""

        for node in self._option_nodes:
            node.destroy()

        self._option_nodes.clear()
        self._option_labels.clear()

        for index, option in enumerate(self.options):
            panel = self.create_child(
                f"Option{index}",
                node_type=Panel,
            )

            panel.size = (
                self.size[0],
                self.option_height,
            )

            panel.anchor = (
                0.0,
                0.0,
            )

            panel.pivot = (
                0.0,
                0.0,
            )

            # Keep the visual option list aligned
            # with the dropdown.
            panel.position = (
                self.size[0] / 2.0,
                self.size[1]
                + 15.0
                + index * self.option_height,
            )

            panel.background = self.option_background

            label = panel.create_child(
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
                15.0,
                0.0,
            )

            label.text = option
            label.text_scale = self.text_scale
            label.text_color = self.text_color

            self._option_nodes.append(panel)
            self._option_labels.append(label)

    def _sync_label(self) -> None:
        value = self.selected_value

        if value is None:
            self._label.text = ""

        else:
            self._label.text = value

        self._arrow.text = (
            "▲"
            if self.opened
            else "▼"
        )

    def _sync_option_layout(self) -> None:
        """Keep option panels aligned with the dropdown size."""

        for index, panel in enumerate(
            self._option_nodes
        ):
            panel.size = (
                self.size[0],
                self.option_height,
            )

            panel.position = (
                self.size[0] / 2.0,
                self.size[1]
                + 15.0
                + index * self.option_height,
            )

    # --------------------------------------------------
    # Option hitbox
    # --------------------------------------------------

    def _option_contains_point(
        self,
        panel: Panel,
        x: float,
        y: float,
    ) -> bool:
        """
        Check an option hitbox against its actual visual bounds.

        The option panels use a top-left pivot, while their position
        is calculated relative to the dropdown center.
        """

        panel_x, panel_y = panel.calculate_position()

        width = panel.size[0]
        height = panel.size[1]

        left = panel_x - width / 2.0
        top = panel_y
        right = left + width
        bottom = top + height

        return (
            left <= x <= right
            and
            top <= y <= bottom
        )

    # --------------------------------------------------
    # Input
    # --------------------------------------------------

    def update_input(
        self,
        ui_input,
    ) -> None:
        if not self.visible or not self.enabled:
            self.opened = False
            self._hovered = False
            self._pressed = False

            self._sync_label()

            return

        mouse_x, mouse_y = ui_input.mouse_position

        self._sync_option_layout()

        # --------------------------------------------------
        # Option input
        # --------------------------------------------------

        if self.opened:
            for index, panel in enumerate(
                self._option_nodes
            ):
                panel_hovered = self._option_contains_point(
                    panel,
                    mouse_x,
                    mouse_y,
                )

                if panel_hovered:
                    panel.background = (
                        self.option_hover_background
                    )

                    if ui_input.mouse_left_pressed:
                        self.set_selected_index(
                            index,
                        )

                        self.opened = False
                        self._sync_label()

                        break

                else:
                    panel.background = (
                        self.option_background
                    )

            # --------------------------------------------------
            # Click outside
            # --------------------------------------------------

            if ui_input.mouse_left_pressed:
                inside_dropdown = self.contains_point(
                    mouse_x,
                    mouse_y,
                )

                inside_option = any(
                    self._option_contains_point(
                        panel,
                        mouse_x,
                        mouse_y,
                    )
                    for panel in self._option_nodes
                )

                if (
                    not inside_dropdown
                    and not inside_option
                ):
                    self.opened = False
                    self._sync_label()

        # --------------------------------------------------
        # Main dropdown field
        # --------------------------------------------------

        hovered = self.contains_point(
            mouse_x,
            mouse_y,
        )

        self._hovered = hovered

        if hovered:
            self.background = (
                self.hover_background
            )

            if ui_input.mouse_left_pressed:
                self.opened = not self.opened
                self._sync_label()

        else:
            self.background = (
                self.background
                if self.opened
                else (
                    32,
                    34,
                    37,
                    255,
                )
            )

        # --------------------------------------------------
        # Children
        # --------------------------------------------------

        if self.opened:
            for child in self._option_nodes:
                child.visible = True

        else:
            for child in self._option_nodes:
                child.visible = False

        self._label.visible = True
        self._arrow.visible = True

    # --------------------------------------------------
    # Rendering
    # --------------------------------------------------

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._sync_option_layout()

        for panel in self._option_nodes:
            panel.visible = self.opened

        super().render(renderer)