from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.ui.output.label import Label
from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.ui_node import UINode


class RadioButton(UINode):
    """
    A focusable radio button UI component.

    Radio buttons can be assigned to a RadioButtonGroup.
    Only one button in a group can be selected at a time.

    Keyboard:
        Space / Enter
            Select this radio button.

        Left / Up
            Focus and select previous button in the group.

        Right / Down
            Focus and select next button in the group.
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
        # State
        # ==========================================================

        self.selected: bool = False

        self._press_started_inside: bool = False
        self._keyboard_pressed: bool = False

        # Prevent a newly focused radio button from processing
        # the same keyboard frame that gave it focus.
        self._skip_keyboard_once: bool = False

        # ==========================================================
        # Group
        # ==========================================================

        self.group: RadioButtonGroup | None = None

        # ==========================================================
        # Appearance
        # ==========================================================

        self.box_size: tuple[float, float] = (
            32.0,
            32.0,
        )

        self.spacing: float = 10.0

        self.text: str = ""

        self.text_scale: float = 1.0

        # ----------------------------------------------------------
        # Colors
        # ----------------------------------------------------------

        self.background: tuple[int, int, int, int] = (
            32,
            34,
            37,
            255,
        )

        self.hover_background: tuple[int, int, int, int] = (
            55,
            58,
            64,
            255,
        )

        self.pressed_background: tuple[int, int, int, int] = (
            25,
            27,
            30,
            255,
        )

        self.selected_background: tuple[int, int, int, int] = (
            45,
            120,
            70,
            255,
        )

        self.selected_hover_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            60,
            145,
            85,
            255,
        )

        self.selected_pressed_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            35,
            100,
            60,
            255,
        )

        self.disabled_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            20,
            21,
            23,
            255,
        )

        # ----------------------------------------------------------
        # Borders
        # ----------------------------------------------------------

        self.border_color: tuple[int, int, int, int] = (
            100,
            100,
            100,
            255,
        )

        self.selected_border_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
            100,
            220,
            130,
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

        self.border_width: float = 2.0
        self.focus_border_width: float = 3.0

        self.border_radius: float = 16.0

        # ----------------------------------------------------------
        # Text
        # ----------------------------------------------------------

        self.text_color: tuple[int, int, int, int] = (
            235,
            235,
            235,
            255,
        )

        self.disabled_text_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
            120,
            120,
            120,
            255,
        )

        # ==========================================================
        # Callback
        # ==========================================================

        self.on_change: Callable[[bool], None] | None = None

        # ==========================================================
        # Children
        # ==========================================================

        self.box = self.create_child(
            "Box",
            node_type=Panel,
        )

        self.label = self.create_child(
            "Label",
            node_type=Label,
        )

        self._sync_layout()
        self._sync_visuals()

    # ==============================================================
    # Group
    # ==============================================================

    def set_group(
        self,
        group: RadioButtonGroup | None,
    ) -> None:
        """
        Assign this radio button to a group.
        """

        if self.group is group:
            return

        previous = self.group

        if previous is not None:
            previous.remove(
                self
            )

        self.group = group

        if group is not None:
            group.add(
                self
            )

    # ==============================================================
    # Selection
    # ==============================================================

    def set_selected(
        self,
        selected: bool,
        *,
        emit: bool = True,
    ) -> None:
        """
        Set the selected state.

        Selecting a grouped radio button automatically deselects all
        other radio buttons in that group.
        """

        selected = bool(
            selected
        )

        if (
            selected
            and self.group is not None
        ):
            self.group.select(
                self,
                emit=emit,
            )

            return

        if self.selected == selected:
            return

        self.selected = selected

        self._sync_visuals()

        if emit:
            callback = self.on_change

            if callback is not None:
                callback(
                    self.selected
                )

    def select(
        self,
    ) -> None:
        """
        Select this radio button.
        """

        if not self.interactive:
            return

        self.set_selected(
            True
        )

    # ==============================================================
    # Focus
    # ==============================================================

    def on_focus(self) -> None:
        """
        Called when the radio button receives focus.

        The keyboard guard prevents the same arrow-key input from
        being processed again by the newly focused radio button in
        the same UIRoot input dispatch.
        """

        self._skip_keyboard_once = True

        self._sync_visuals()

    def on_blur(self) -> None:
        self._keyboard_pressed = False
        self._press_started_inside = False

        self.set_pressed(
            False
        )

        self._sync_visuals()

    # ==============================================================
    # Size
    # ==============================================================

    @property
    def content_size(
        self,
    ) -> tuple[float, float]:
        """
        Return the size of the complete radio button.
        """

        label_width = max(
            0.0,
            len(self.text)
            * 16.0
            * self.text_scale,
        )

        label_height = (
            32.0
            * self.text_scale
        )

        return (
            self.box_size[0]
            + self.spacing
            + label_width,
            max(
                self.box_size[1],
                label_height,
            ),
        )

    # ==============================================================
    # Layout
    # ==============================================================

    def _sync_layout(self) -> None:
        """
        Synchronize child layout.
        """

        self.size = (
            self.content_size
        )

        # ----------------------------------------------------------
        # Circle
        # ----------------------------------------------------------

        self.box.size = (
            self.box_size
        )

        self.box.anchor = (
            0.0,
            0.5,
        )

        self.box.pivot = (
            0.0,
            0.5,
        )

        self.box.position = (
            0.0,
            0.0,
        )

        # ----------------------------------------------------------
        # Label
        # ----------------------------------------------------------

        self.label.text = (
            self.text
        )

        self.label.scale = (
            self.text_scale
        )

        self.label.anchor = (
            0.0,
            0.5,
        )

        self.label.pivot = (
            0.0,
            0.5,
        )

        self.label.position = (
            self.box_size[0]
            + self.spacing,
            0.0,
        )

    # ==============================================================
    # Visual state
    # ==============================================================

    def _sync_visuals(self) -> None:
        """
        Synchronize appearance.
        """

        # ----------------------------------------------------------
        # Disabled
        # ----------------------------------------------------------

        if not self.enabled:
            self.box.background = (
                self.disabled_background
            )

            self.box.border_color = (
                self.border_color
            )

            self.box.border_width = (
                self.border_width
            )

            self.label.color = (
                self.disabled_text_color
            )

            return

        self.label.color = (
            self.text_color
        )

        # ----------------------------------------------------------
        # Background
        # ----------------------------------------------------------

        if self.selected:
            if self.pressed:
                self.box.background = (
                    self.selected_pressed_background
                )

            elif self.hovered:
                self.box.background = (
                    self.selected_hover_background
                )

            else:
                self.box.background = (
                    self.selected_background
                )

        else:
            if self.pressed:
                self.box.background = (
                    self.pressed_background
                )

            elif self.hovered:
                self.box.background = (
                    self.hover_background
                )

            else:
                self.box.background = (
                    self.background
                )

        # ----------------------------------------------------------
        # Border
        # ----------------------------------------------------------

        if self.focused:
            self.box.border_color = (
                self.focus_border_color
            )

            self.box.border_width = (
                self.focus_border_width
            )

        elif self.selected:
            self.box.border_color = (
                self.selected_border_color
            )

            self.box.border_width = (
                self.border_width
            )

        else:
            self.box.border_color = (
                self.border_color
            )

            self.box.border_width = (
                self.border_width
            )

        self.box.border_radius = (
            self.border_radius
        )

    # ==============================================================
    # Hit testing
    # ==============================================================

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        """
        Check whether a point is inside the complete radio button.
        """

        rect_x, rect_y = (
            self.calculate_position()
        )

        width, height = (
            self.content_size
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
    # Keyboard
    # ==============================================================

    def _handle_keyboard(
        self,
        ui_input,
    ) -> None:
        if not self.focused:
            self._keyboard_pressed = False
            return

        # ----------------------------------------------------------
        # Input-frame guard
        # ----------------------------------------------------------

        if self._skip_keyboard_once:
            self._skip_keyboard_once = False
            return

        # ----------------------------------------------------------
        # Previous radio button
        # ----------------------------------------------------------

        if (
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_LEFT
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_UP
            )
        ):
            if self.group is not None:
                self.group.select_previous(
                    self
                )

            return

        # ----------------------------------------------------------
        # Next radio button
        # ----------------------------------------------------------

        if (
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_RIGHT
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_DOWN
            )
        ):
            if self.group is not None:
                self.group.select_next(
                    self
                )

            return

        # ----------------------------------------------------------
        # Activate
        # ----------------------------------------------------------

        activate_pressed = (
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_SPACE
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_RETURN
            )
            or
            ui_input.key_pressed(
                sdl3.SDL_SCANCODE_KP_ENTER
            )
        )

        if activate_pressed:
            self._keyboard_pressed = True

            self.set_pressed(
                True
            )

        # ----------------------------------------------------------
        # Activate release
        # ----------------------------------------------------------

        if self._keyboard_pressed:
            released = (
                ui_input.key_released(
                    sdl3.SDL_SCANCODE_SPACE
                )
                or
                ui_input.key_released(
                    sdl3.SDL_SCANCODE_RETURN
                )
                or
                ui_input.key_released(
                    sdl3.SDL_SCANCODE_KP_ENTER
                )
            )

            if released:
                self._keyboard_pressed = False

                self.set_pressed(
                    False
                )

                self.select()

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        """
        Process mouse and keyboard input.
        """

        if not self.interactive:
            self.reset_interaction_state()

            self._press_started_inside = False
            self._keyboard_pressed = False

            self._sync_visuals()

            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self.update_hover(
            mouse_x,
            mouse_y,
        )

        # ==========================================================
        # Mouse
        # ==========================================================

        if ui_input.mouse_left_pressed:
            self._press_started_inside = (
                self.hovered
            )

            if self._press_started_inside:
                self.set_pressed(
                    True
                )

        if ui_input.mouse_left_released:
            should_select = (
                self._press_started_inside
                and self.hovered
            )

            self._press_started_inside = False

            if not self._keyboard_pressed:
                self.set_pressed(
                    False
                )

            if should_select:
                self.select()

        # ==========================================================
        # Keyboard
        # ==========================================================

        self._handle_keyboard(
            ui_input
        )

        # ==========================================================
        # Visuals
        # ==========================================================

        self._sync_layout()
        self._sync_visuals()

    # ==============================================================
    # Render
    # ==============================================================

    def render(
        self,
        renderer,
    ) -> None:
        """
        Render the radio button.
        """

        if not self.visible:
            return

        self._sync_layout()
        self._sync_visuals()

        self.box.render(
            renderer
        )

        self.label.render(
            renderer
        )


class RadioButtonGroup:
    """
    Group of radio buttons.

    Only one radio button can be selected at a time.

    Arrow-key navigation wraps around the group.
    """

    def __init__(
        self,
    ) -> None:
        self.buttons: list[
            RadioButton
        ] = []

    # ==============================================================
    # Membership
    # ==============================================================

    def add(
        self,
        button: RadioButton,
    ) -> None:
        """
        Add a radio button to the group.
        """

        if button in self.buttons:
            return

        if (
            button.group is not None
            and button.group is not self
        ):
            button.group.remove(
                button
            )

        self.buttons.append(
            button
        )

        button.group = self

        if button.selected:
            self.select(
                button,
                emit=False,
            )

    def remove(
        self,
        button: RadioButton,
    ) -> None:
        """
        Remove a radio button from the group.
        """

        if button not in self.buttons:
            return

        self.buttons.remove(
            button
        )

        if button.group is self:
            button.group = None

    # ==============================================================
    # Selection
    # ==============================================================

    def select(
        self,
        button: RadioButton,
        *,
        emit: bool = True,
    ) -> None:
        """
        Select one button and deselect all others.
        """

        if button not in self.buttons:
            self.add(
                button
            )

        for other in self.buttons:
            new_selected = (
                other is button
            )

            changed = (
                other.selected
                != new_selected
            )

            other.selected = (
                new_selected
            )

            other._sync_visuals()

            if (
                emit
                and changed
            ):
                callback = (
                    other.on_change
                )

                if callback is not None:
                    callback(
                        new_selected
                    )

    # ==============================================================
    # Navigation
    # ==============================================================

    def _interactive_buttons(
        self,
    ) -> list[RadioButton]:
        """
        Return buttons available for keyboard navigation.
        """

        return [
            button
            for button in self.buttons
            if button.interactive
        ]

    def select_next(
        self,
        current: RadioButton,
    ) -> bool:
        """
        Focus and select the next available radio button.
        """

        buttons = (
            self._interactive_buttons()
        )

        if not buttons:
            return False

        if current not in buttons:
            target = buttons[0]

        else:
            index = buttons.index(
                current
            )

            target = buttons[
                (index + 1)
                % len(buttons)
            ]

        self.select(
            target
        )

        target.focus()

        return True

    def select_previous(
        self,
        current: RadioButton,
    ) -> bool:
        """
        Focus and select the previous available radio button.
        """

        buttons = (
            self._interactive_buttons()
        )

        if not buttons:
            return False

        if current not in buttons:
            target = buttons[-1]

        else:
            index = buttons.index(
                current
            )

            target = buttons[
                (index - 1)
                % len(buttons)
            ]

        self.select(
            target
        )

        target.focus()

        return True

    # ==============================================================
    # State
    # ==============================================================

    @property
    def selected(
        self,
    ) -> RadioButton | None:
        """
        Return the selected radio button.
        """

        for button in self.buttons:
            if button.selected:
                return button

        return None

    @property
    def selected_index(
        self,
    ) -> int:
        """
        Return the selected button index.

        Returns -1 when nothing is selected.
        """

        selected = self.selected

        if selected is None:
            return -1

        try:
            return self.buttons.index(
                selected
            )

        except ValueError:
            return -1