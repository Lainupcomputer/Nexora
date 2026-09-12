from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.label import Label
from nexora.nodes.panel import Panel
from nexora.nodes.ui_node import UINode


class CheckBox(UINode):
    """
    A focusable checkbox UI component.

    Interaction:

        Mouse:
            Click toggles the checkbox.

        Keyboard:
            Space toggles the checkbox.
            Enter toggles the checkbox.
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

        self.checked: bool = False

        # ==========================================================
        # Content
        # ==========================================================

        self.text: str = ""

        self.text_scale: float = 1.0

        # ==========================================================
        # Size / layout
        # ==========================================================

        self.box_size: float = 28.0
        self.spacing: float = 10.0

        self.size = (
            220.0,
            40.0,
        )

        # ==========================================================
        # Colors
        # ==========================================================

        self.box_background: tuple[
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

        self.box_hover_background: tuple[
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

        self.box_pressed_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            25,
            27,
            30,
            255,
        )

        self.box_checked_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            70,
            130,
            220,
            255,
        )

        self.box_disabled_background: tuple[
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

        self.text_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
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

        self.check_color: tuple[
            int,
            int,
            int,
            int,
        ] = (
            255,
            255,
            255,
            255,
        )

        # ==========================================================
        # Internal state
        # ==========================================================

        self._press_started_inside: bool = False
        self._keyboard_pressed: bool = False

        # ==========================================================
        # Callback
        # ==========================================================

        self.on_change: (
            Callable[[bool], None]
            | None
        ) = None

        # ==========================================================
        # Child nodes
        # ==========================================================

        self._box = self.create_child(
            "Box",
            node_type=Panel,
        )

        self._check = self._box.create_child(
            "Check",
            node_type=Label,
        )

        self._label = self.create_child(
            "Label",
            node_type=Label,
        )

        # ----------------------------------------------------------
        # Check glyph
        # ----------------------------------------------------------

        self._check.text = "✓"

        self._check.anchor = (
            0.5,
            0.5,
        )

        self._check.pivot = (
            0.5,
            0.5,
        )

        self._check.position = (
            0.0,
            0.0,
        )

        self._check.text_color = (
            self.check_color
        )

        # ----------------------------------------------------------
        # Text label
        # ----------------------------------------------------------

        self._label.anchor = (
            0.0,
            0.5,
        )

        self._label.pivot = (
            0.0,
            0.5,
        )

        self._sync_layout()
        self._sync_visuals()

    # ==============================================================
    # State
    # ==============================================================

    def set_checked(
        self,
        checked: bool,
        *,
        emit: bool = True,
    ) -> None:
        """
        Set the checked state.
        """

        checked = bool(checked)

        if self.checked == checked:
            return

        self.checked = checked

        self._sync_visuals()

        if emit:
            callback = self.on_change

            if callback is not None:
                callback(
                    self.checked
                )

    def toggle(self) -> None:
        """
        Toggle the checked state.
        """

        if not self.interactive:
            return

        self.set_checked(
            not self.checked
        )

    # ==============================================================
    # Focus
    # ==============================================================

    def on_focus(self) -> None:
        self._sync_visuals()

    def on_blur(self) -> None:
        self._keyboard_pressed = False
        self._press_started_inside = False

        self.set_pressed(
            False
        )

        self._sync_visuals()

    # ==============================================================
    # Layout
    # ==============================================================

    def _sync_layout(self) -> None:
        width, height = self.size

        # ----------------------------------------------------------
        # Box
        # ----------------------------------------------------------

        self._box.size = (
            self.box_size,
            self.box_size,
        )

        self._box.anchor = (
            0.0,
            0.5,
        )

        self._box.pivot = (
            0.0,
            0.5,
        )

        self._box.position = (
            0.0,
            0.0,
        )

        # ----------------------------------------------------------
        # Check
        # ----------------------------------------------------------

        self._check.text_scale = (
            self.text_scale
        )

        # ----------------------------------------------------------
        # Label
        # ----------------------------------------------------------

        self._label.text = self.text

        self._label.text_scale = (
            self.text_scale
        )

        self._label.position = (
            self.box_size
            + self.spacing,
            0.0,
        )

    # ==============================================================
    # Visuals
    # ==============================================================

    def _sync_visuals(self) -> None:
        # ----------------------------------------------------------
        # Box background
        # ----------------------------------------------------------

        if not self.enabled:
            self._box.background = (
                self.box_disabled_background
            )

        elif self.pressed:
            self._box.background = (
                self.box_pressed_background
            )

        elif self.checked:
            self._box.background = (
                self.box_checked_background
            )

        elif self.hovered:
            self._box.background = (
                self.box_hover_background
            )

        else:
            self._box.background = (
                self.box_background
            )

        # ----------------------------------------------------------
        # Border
        # ----------------------------------------------------------

        if (
            self.focused
            and self.enabled
        ):
            self._box.border_color = (
                self.focus_border_color
            )

            self._box.border_width = 2.0

        else:
            self._box.border_color = (
                self.normal_border_color
            )

            self._box.border_width = 1.0

        self._box.border_radius = 4.0

        # ----------------------------------------------------------
        # Check mark
        # ----------------------------------------------------------

        self._check.visible = (
            self.checked
        )

        self._check.text_color = (
            self.check_color
        )

        # ----------------------------------------------------------
        # Label
        # ----------------------------------------------------------

        if self.enabled:
            self._label.text_color = (
                self.text_color
            )
        else:
            self._label.text_color = (
                self.disabled_text_color
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
        # Key down
        # ----------------------------------------------------------

        if (
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
        ):
            self._keyboard_pressed = True

            self.set_pressed(
                True
            )

        # ----------------------------------------------------------
        # Key release
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

                self.toggle()

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
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
            should_toggle = (
                self._press_started_inside
                and self.hovered
            )

            self._press_started_inside = False

            if not self._keyboard_pressed:
                self.set_pressed(
                    False
                )

            if should_toggle:
                self.toggle()

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
    # Rendering
    # ==============================================================

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._sync_layout()
        self._sync_visuals()

        self._box.render(
            renderer
        )

        self._label.render(
            renderer
        )