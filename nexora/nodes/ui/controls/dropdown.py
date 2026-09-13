from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.output.label import Label


class Dropdown(Panel):
    """
    A focusable dropdown selection UI component.

    Keyboard controls:

        Enter / Space
            Open the dropdown.
            When opened, select the highlighted option.

        Up / Down
            Move the highlighted option.

        Home
            Highlight the first option.

        End
            Highlight the last option.

        Escape
            Close the dropdown.

        Tab / Shift+Tab
            Handled globally by UIRoot.
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
        # Dropdown state
        # ==========================================================

        self.options: list[str] = []

        self.selected_index: int = -1

        # Option currently highlighted while the dropdown is open.
        self.highlighted_index: int = -1

        self.opened: bool = False

        self.on_change: (
            Callable[[int, str | None], None]
            | None
        ) = None

        # ==========================================================
        # Appearance
        # ==========================================================

        self.normal_background = (
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

        self.focus_background = (
            40,
            44,
            52,
            255,
        )

        self.pressed_background = (
            25,
            27,
            30,
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

        self.option_selected_background = (
            42,
            70,
            105,
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

        # ----------------------------------------------------------
        # Border
        # ----------------------------------------------------------

        self.normal_border_color = (
            70,
            72,
            76,
            255,
        )

        self.focus_border_color = (
            80,
            140,
            220,
            255,
        )

        self.normal_border_width: float = 1.0
        self.focus_border_width: float = 2.0

        # ----------------------------------------------------------
        # Layout
        # ----------------------------------------------------------

        self.option_height: float = 40.0
        self.text_scale: float = 1.0

        # ==========================================================
        # Internal state
        # ==========================================================

        self._hovered: bool = False
        self._pressed: bool = False

        # ==========================================================
        # Internal nodes
        # ==========================================================

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

        self._label.text_scale = (
            self.text_scale
        )

        self._label.text_color = (
            self.text_color
        )

        # ----------------------------------------------------------
        # Arrow
        # ----------------------------------------------------------

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

        self._arrow.text_scale = (
            self.text_scale
        )

        self._arrow.text_color = (
            self.text_color
        )

        # ----------------------------------------------------------
        # Options
        # ----------------------------------------------------------

        self._option_nodes: list[Panel] = []
        self._option_labels: list[Label] = []

        # ----------------------------------------------------------
        # Initial visuals
        # ----------------------------------------------------------

        self.background = (
            self.normal_background
        )

        self.border_color = (
            self.normal_border_color
        )

        self.border_width = (
            self.normal_border_width
        )

        self._sync_label()
        self._sync_visuals()

    # ==============================================================
    # Properties
    # ==============================================================

    @property
    def selected_value(
        self,
    ) -> str | None:
        """
        Return the currently selected value.
        """

        if (
            self.selected_index < 0
            or
            self.selected_index
            >= len(self.options)
        ):
            return None

        return self.options[
            self.selected_index
        ]

    @property
    def highlighted_value(
        self,
    ) -> str | None:
        """
        Return the currently highlighted value.
        """

        if (
            self.highlighted_index < 0
            or
            self.highlighted_index
            >= len(self.options)
        ):
            return None

        return self.options[
            self.highlighted_index
        ]

    # ==============================================================
    # Focus
    # ==============================================================

    def on_focus(self) -> None:
        self._sync_visuals()

    def on_blur(self) -> None:
        """
        Close the dropdown when it loses focus.
        """

        self.opened = False
        self._pressed = False

        self._sync_label()
        self._sync_visuals()
        self._sync_option_visuals()

    # ==============================================================
    # Opening / closing
    # ==============================================================

    def open(self) -> None:
        """
        Open the dropdown.
        """

        if (
            not self.enabled
            or not self.visible
            or not self.options
        ):
            return

        self.opened = True

        # Start keyboard navigation on the current selection.
        if (
            0
            <= self.selected_index
            < len(self.options)
        ):
            self.highlighted_index = (
                self.selected_index
            )

        else:
            self.highlighted_index = 0

        self._sync_label()
        self._sync_visuals()
        self._sync_option_visuals()

    def close(self) -> None:
        """
        Close the dropdown.
        """

        if not self.opened:
            return

        self.opened = False

        self._sync_label()
        self._sync_visuals()
        self._sync_option_visuals()

    def toggle(self) -> None:
        """
        Toggle the dropdown.
        """

        if self.opened:
            self.close()
        else:
            self.open()

    # ==============================================================
    # Options
    # ==============================================================

    def set_options(
        self,
        options: list[str] | tuple[str, ...],
    ) -> None:
        """
        Replace all dropdown options.
        """

        self.options = [
            str(option)
            for option in options
        ]

        if not self.options:
            self.selected_index = -1
            self.highlighted_index = -1
            self.opened = False

        elif self.selected_index < 0:
            self.selected_index = 0
            self.highlighted_index = 0

        elif (
            self.selected_index
            >= len(self.options)
        ):
            self.selected_index = (
                len(self.options) - 1
            )

            self.highlighted_index = (
                self.selected_index
            )

        else:
            self.highlighted_index = (
                self.selected_index
            )

        self._rebuild_options()
        self._sync_label()
        self._sync_visuals()

    def add_option(
        self,
        option: str,
    ) -> None:
        """
        Add an option.
        """

        self.options.append(
            str(option)
        )

        if self.selected_index < 0:
            self.selected_index = 0

        if self.highlighted_index < 0:
            self.highlighted_index = (
                self.selected_index
            )

        self._rebuild_options()
        self._sync_label()
        self._sync_visuals()

    def remove_option(
        self,
        index: int,
    ) -> None:
        """
        Remove an option by index.
        """

        if (
            index < 0
            or index >= len(self.options)
        ):
            return

        del self.options[index]

        if not self.options:
            self.selected_index = -1
            self.highlighted_index = -1
            self.opened = False

        else:
            # ------------------------------------------------------
            # Selected index
            # ------------------------------------------------------

            if (
                self.selected_index
                >= len(self.options)
            ):
                self.selected_index = (
                    len(self.options) - 1
                )

            elif (
                index
                < self.selected_index
            ):
                self.selected_index -= 1

            elif (
                index
                == self.selected_index
            ):
                self.selected_index = min(
                    self.selected_index,
                    len(self.options) - 1,
                )

            # ------------------------------------------------------
            # Highlight
            # ------------------------------------------------------

            self.highlighted_index = (
                self.selected_index
            )

        self._rebuild_options()
        self._sync_label()
        self._sync_visuals()

    def clear_options(self) -> None:
        """
        Remove all options.
        """

        self.options.clear()

        self.selected_index = -1
        self.highlighted_index = -1

        self.opened = False

        self._rebuild_options()
        self._sync_label()
        self._sync_visuals()

    # ==============================================================
    # Selection
    # ==============================================================

    def set_selected_index(
        self,
        index: int,
        *,
        emit: bool = True,
    ) -> None:
        """
        Select an option by index.
        """

        if not self.options:
            self.selected_index = -1
            self.highlighted_index = -1

            self._sync_label()
            return

        index = max(
            0,
            min(
                int(index),
                len(self.options) - 1,
            ),
        )

        changed = (
            index != self.selected_index
        )

        self.selected_index = index
        self.highlighted_index = index

        self._sync_label()
        self._sync_option_visuals()

        if (
            emit
            and changed
        ):
            callback = self.on_change

            if callback is not None:
                callback(
                    self.selected_index,
                    self.selected_value,
                )

    def select_highlighted(self) -> None:
        """
        Select the currently highlighted option.
        """

        if not self.options:
            return

        if not (
            0
            <= self.highlighted_index
            < len(self.options)
        ):
            return

        self.set_selected_index(
            self.highlighted_index,
        )

        self.close()

    # ==============================================================
    # Highlight navigation
    # ==============================================================

    def highlight_next(self) -> None:
        """
        Highlight the next option.

        Wraps around to the first option.
        """

        if not self.options:
            return

        if self.highlighted_index < 0:
            self.highlighted_index = 0

        else:
            self.highlighted_index = (
                self.highlighted_index + 1
            ) % len(self.options)

        self._sync_option_visuals()

    def highlight_previous(self) -> None:
        """
        Highlight the previous option.

        Wraps around to the last option.
        """

        if not self.options:
            return

        if self.highlighted_index < 0:
            self.highlighted_index = (
                len(self.options) - 1
            )

        else:
            self.highlighted_index = (
                self.highlighted_index - 1
            ) % len(self.options)

        self._sync_option_visuals()

    def highlight_first(self) -> None:
        """
        Highlight the first option.
        """

        if not self.options:
            return

        self.highlighted_index = 0

        self._sync_option_visuals()

    def highlight_last(self) -> None:
        """
        Highlight the last option.
        """

        if not self.options:
            return

        self.highlighted_index = (
            len(self.options) - 1
        )

        self._sync_option_visuals()

    # ==============================================================
    # Internal option creation
    # ==============================================================

    def _rebuild_options(self) -> None:
        """
        Rebuild the option panels.
        """

        for node in self._option_nodes:
            node.destroy()

        self._option_nodes.clear()
        self._option_labels.clear()

        for index, option in enumerate(
            self.options
        ):
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

            panel.position = (
                self.size[0] / 2.0,
                self.size[1]
                + 15.0
                + index
                * self.option_height,
            )

            panel.background = (
                self.option_background
            )

            panel.visible = self.opened

            # ------------------------------------------------------
            # Label
            # ------------------------------------------------------

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

            label.text_scale = (
                self.text_scale
            )

            label.text_color = (
                self.text_color
            )

            self._option_nodes.append(
                panel
            )

            self._option_labels.append(
                label
            )

        self._sync_option_visuals()

    # ==============================================================
    # Visual synchronization
    # ==============================================================

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

    def _sync_visuals(self) -> None:
        """
        Synchronize the main dropdown field.
        """

        if not self.enabled:
            self.background = (
                self.normal_background
            )

            self._label.text_color = (
                self.disabled_color
            )

            self._arrow.text_color = (
                self.disabled_color
            )

        else:
            self._label.text_color = (
                self.text_color
            )

            self._arrow.text_color = (
                self.text_color
            )

            if self._pressed:
                self.background = (
                    self.pressed_background
                )

            elif self._hovered:
                self.background = (
                    self.hover_background
                )

            elif self.focused:
                self.background = (
                    self.focus_background
                )

            else:
                self.background = (
                    self.normal_background
                )

        # ----------------------------------------------------------
        # Focus border
        # ----------------------------------------------------------

        if (
            self.focused
            and self.enabled
        ):
            self.border_color = (
                self.focus_border_color
            )

            self.border_width = (
                self.focus_border_width
            )

        else:
            self.border_color = (
                self.normal_border_color
            )

            self.border_width = (
                self.normal_border_width
            )

    def _sync_option_layout(self) -> None:
        """
        Keep option panels aligned with the dropdown.
        """

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
                + index
                * self.option_height,
            )

    def _sync_option_visuals(self) -> None:
        """
        Update option visibility and backgrounds.
        """

        for index, panel in enumerate(
            self._option_nodes
        ):
            panel.visible = self.opened

            if not self.opened:
                panel.background = (
                    self.option_background
                )

                continue

            if (
                index
                == self.highlighted_index
            ):
                panel.background = (
                    self.option_hover_background
                )

            elif (
                index
                == self.selected_index
            ):
                panel.background = (
                    self.option_selected_background
                )

            else:
                panel.background = (
                    self.option_background
                )

    # ==============================================================
    # Option hit testing
    # ==============================================================

    def _option_contains_point(
        self,
        panel: Panel,
        x: float,
        y: float,
    ) -> bool:
        """
        Check an option hitbox against its actual visual bounds.
        """

        panel_x, panel_y = (
            panel.calculate_position()
        )

        width = panel.size[0]
        height = panel.size[1]

        left = (
            panel_x
            - width / 2.0
        )

        top = panel_y

        right = (
            left + width
        )

        bottom = (
            top + height
        )

        return (
            left <= x <= right
            and
            top <= y <= bottom
        )

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        """
        Return whether the point is inside the dropdown.

        While opened, the option list is considered part of the
        dropdown hitbox. This is important for UIRoot focus handling:
        clicking an option must not clear focus before the dropdown
        has a chance to process the click.
        """

        if super().contains_point(
            x,
            y,
        ):
            return True

        if not self.opened:
            return False

        return any(
            self._option_contains_point(
                panel,
                x,
                y,
            )
            for panel in self._option_nodes
        )

    # ==============================================================
    # Keyboard
    # ==============================================================

    def _handle_keyboard(
        self,
        ui_input,
    ) -> None:
        """
        Handle keyboard dropdown interaction.
        """

        if not self.focused:
            return

        # ----------------------------------------------------------
        # Escape
        # ----------------------------------------------------------

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_ESCAPE
        ):
            if self.opened:
                self.close()

            return

        # ----------------------------------------------------------
        # Enter / Space
        # ----------------------------------------------------------

        activate = (
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
        )

        if activate:
            if self.opened:
                self.select_highlighted()
            else:
                self.open()

            return

        # ----------------------------------------------------------
        # Down
        # ----------------------------------------------------------

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_DOWN
        ):
            if not self.opened:
                self.open()

                # Start one item after the selected item.
                if len(self.options) > 1:
                    self.highlight_next()

            else:
                self.highlight_next()

            return

        # ----------------------------------------------------------
        # Up
        # ----------------------------------------------------------

        if ui_input.key_pressed(
            sdl3.SDL_SCANCODE_UP
        ):
            if not self.opened:
                self.open()

                if len(self.options) > 1:
                    self.highlight_previous()

            else:
                self.highlight_previous()

            return

        # ----------------------------------------------------------
        # Home / End
        # ----------------------------------------------------------

        if (
            self.opened
            and ui_input.key_pressed(
                sdl3.SDL_SCANCODE_HOME
            )
        ):
            self.highlight_first()
            return

        if (
            self.opened
            and ui_input.key_pressed(
                sdl3.SDL_SCANCODE_END
            )
        ):
            self.highlight_last()

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        if (
            not self.visible
            or not self.enabled
        ):
            self.opened = False
            self._hovered = False
            self._pressed = False

            self._sync_label()
            self._sync_visuals()
            self._sync_option_visuals()

            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self._sync_option_layout()

        # ==========================================================
        # Keyboard
        # ==========================================================

        self._handle_keyboard(
            ui_input
        )

        # ==========================================================
        # Option mouse input
        # ==========================================================

        option_clicked = False

        if self.opened:
            for index, panel in enumerate(
                self._option_nodes
            ):
                panel_hovered = (
                    self._option_contains_point(
                        panel,
                        mouse_x,
                        mouse_y,
                    )
                )

                if panel_hovered:
                    self.highlighted_index = (
                        index
                    )

                    if (
                        ui_input
                        .mouse_left_pressed
                    ):
                        self.set_selected_index(
                            index
                        )

                        self.close()

                        option_clicked = True

                        break

            self._sync_option_visuals()

        # ==========================================================
        # Main dropdown field
        # ==========================================================

        # Use Panel's hitbox specifically here.
        # self.contains_point() also contains opened options.
        main_hovered = (
            super().contains_point(
                mouse_x,
                mouse_y,
            )
        )

        self._hovered = main_hovered

        if (
            main_hovered
            and ui_input.mouse_left_pressed
            and not option_clicked
        ):
            self._pressed = True

            self.toggle()

        if ui_input.mouse_left_released:
            self._pressed = False

        # ==========================================================
        # Click outside
        # ==========================================================

        if (
            self.opened
            and ui_input.mouse_left_pressed
            and not option_clicked
        ):
            inside_dropdown = (
                self.contains_point(
                    mouse_x,
                    mouse_y,
                )
            )

            if not inside_dropdown:
                self.close()

        # ==========================================================
        # Synchronize
        # ==========================================================

        self._sync_label()
        self._sync_visuals()
        self._sync_option_visuals()

    # ==============================================================
    # Rendering
    # ==============================================================

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._sync_option_layout()
        self._sync_label()
        self._sync_visuals()
        self._sync_option_visuals()

        super().render(
            renderer
        )