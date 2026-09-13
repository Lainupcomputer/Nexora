from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.ui.output.label import Label
from nexora.nodes.ui.containers.panel import Panel


class Button(Panel):
    """
    A clickable and focusable UI button.

    Interaction:
        Mouse:
            Press + release inside the button triggers the click.

        Keyboard:
            Enter or Space triggers the button while focused.
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

        # ----------------------------------------------------------
        # Focus
        # ----------------------------------------------------------

        self.focusable = True

        # ----------------------------------------------------------
        # Text
        # ----------------------------------------------------------

        self.text: str = ""

        self.text_scale: float = 1.0

        self.text_color: tuple[
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

        # ----------------------------------------------------------
        # Visual states
        # ----------------------------------------------------------

        self.hovered: bool = False
        self.pressed: bool = False

        self.normal_background: tuple[
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

        self.hover_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            45,
            48,
            52,
            255,
        )

        self.pressed_background: tuple[
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

        self.focus_background: tuple[
            int,
            int,
            int,
            int,
        ] = (
            40,
            44,
            52,
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

        # ----------------------------------------------------------
        # Border
        # ----------------------------------------------------------

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

        self.normal_border_width: float = 1.0
        self.focus_border_width: float = 2.0

        # ----------------------------------------------------------
        # Click state
        # ----------------------------------------------------------

        self._press_started_inside: bool = False
        self._keyboard_pressed: bool = False

        self.on_click: Callable[[], None] | None = None

        # ----------------------------------------------------------
        # Internal label
        # ----------------------------------------------------------

        self._label = Label(
            f"{name}_Label",
            world,
        )

        self.add_child(
            self._label,
        )

        self._sync_label()
        self._sync_visuals()

    # ==============================================================
    # Focus
    # ==============================================================

    def on_focus(self) -> None:
        self._sync_visuals()

    def on_blur(self) -> None:
        self.pressed = False
        self._keyboard_pressed = False
        self._press_started_inside = False

        self._sync_visuals()

    # ==============================================================
    # Click
    # ==============================================================

    def click(self) -> None:
        """
        Trigger the button callback.

        Does nothing while the button is disabled or invisible.
        """

        if (
            not self.visible
            or not self.enabled
        ):
            return

        callback = self.on_click

        if callback is not None:
            callback()

    # ==============================================================
    # State
    # ==============================================================

    def _sync_label(self) -> None:
        self._label.text = self.text
        self._label.scale = self.text_scale

        if self.enabled:
            self._label.color = (
                self.text_color
            )

        else:
            self._label.color = (
                self.disabled_text_color
            )

        self._label.anchor = (
            0.5,
            0.5,
        )

        self._label.pivot = (
            0.5,
            0.5,
        )

        self._label.position = (
            0.0,
            0.0,
        )

    def _sync_visuals(self) -> None:
        # ----------------------------------------------------------
        # Disabled
        # ----------------------------------------------------------

        if not self.enabled:
            self.background = (
                self.disabled_background
            )

            self.border_color = (
                self.normal_border_color
            )

            self.border_width = (
                self.normal_border_width
            )

            return

        # ----------------------------------------------------------
        # Pressed
        # ----------------------------------------------------------

        if self.pressed:
            self.background = (
                self.pressed_background
            )

        # ----------------------------------------------------------
        # Hover
        # ----------------------------------------------------------

        elif self.hovered:
            self.background = (
                self.hover_background
            )

        # ----------------------------------------------------------
        # Focus
        # ----------------------------------------------------------

        elif self.focused:
            self.background = (
                self.focus_background
            )

        # ----------------------------------------------------------
        # Normal
        # ----------------------------------------------------------

        else:
            self.background = (
                self.normal_background
            )

        # ----------------------------------------------------------
        # Focus border
        # ----------------------------------------------------------

        if self.focused:
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

    # ==============================================================
    # Rendering
    # ==============================================================

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        self._sync_label()
        self._sync_visuals()

        super().render(
            renderer,
        )

    # ==============================================================
    # Input
    # ==============================================================

    def update_input(
        self,
        ui_input,
    ) -> None:
        """
        Update the button's input state.

        Mouse:
            Click occurs when the mouse is pressed inside the button
            and released while still inside.

        Keyboard:
            Enter or Space triggers the button while it is focused.
        """

        if (
            not self.visible
            or not self.enabled
        ):
            self.hovered = False
            self.pressed = False
            self._press_started_inside = False
            self._keyboard_pressed = False

            self._sync_visuals()

            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self.hovered = self.contains_point(
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

        mouse_pressed_visual = (
            self._press_started_inside
            and ui_input.mouse_left_down
            and self.hovered
        )

        if ui_input.mouse_left_released:
            should_click = (
                self._press_started_inside
                and self.hovered
            )

            self._press_started_inside = False

            if should_click:
                self.click()

        # ==========================================================
        # Keyboard
        # ==========================================================

        keyboard_down = False

        if self.focused:
            keyboard_down = (
                ui_input.key_down(
                    sdl3.SDL_SCANCODE_RETURN
                )
                or
                ui_input.key_down(
                    sdl3.SDL_SCANCODE_KP_ENTER
                )
                or
                ui_input.key_down(
                    sdl3.SDL_SCANCODE_SPACE
                )
            )

            # ------------------------------------------------------
            # Keyboard press
            # ------------------------------------------------------

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
                self._keyboard_pressed = True

            # ------------------------------------------------------
            # Keyboard release
            #
            # Trigger click on release instead of press so the
            # pressed visual state behaves like a real button.
            # ------------------------------------------------------

            if self._keyboard_pressed:
                released = (
                    ui_input.key_released(
                        sdl3.SDL_SCANCODE_RETURN
                    )
                    or
                    ui_input.key_released(
                        sdl3.SDL_SCANCODE_KP_ENTER
                    )
                    or
                    ui_input.key_released(
                        sdl3.SDL_SCANCODE_SPACE
                    )
                )

                if released:
                    self._keyboard_pressed = False

                    self.click()

        else:
            self._keyboard_pressed = False

        # ==========================================================
        # Final pressed state
        # ==========================================================

        self.pressed = (
            mouse_pressed_visual
            or (
                self.focused
                and self._keyboard_pressed
                and keyboard_down
            )
        )

        self._sync_visuals()