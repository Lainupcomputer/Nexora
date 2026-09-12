from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.label import Label
from nexora.nodes.panel import Panel
from nexora.nodes.ui_node import UINode


class TextInput(UINode):
    """
    A single-line text input UI component.

    The node handles:
        - focus through UIRoot
        - text display
        - placeholder display
        - cursor position
        - keyboard text input
        - backspace / delete
        - left / right navigation
        - home / end navigation
        - enter / submit
        - visual focus state

    Focus ownership is managed centrally by UIRoot.
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
        # Content
        # ----------------------------------------------------------

        self.text: str = ""
        self.placeholder: str = ""

        self.max_length: int = 0

        self.text_scale: float = 1.0

        # ----------------------------------------------------------
        # Interaction
        # ----------------------------------------------------------

        self.focusable = True

        self.hovered: bool = False
        self.pressed: bool = False

        self.cursor_position: int = 0

        # ----------------------------------------------------------
        # Appearance
        # ----------------------------------------------------------

        self.background: tuple[int, int, int, int] = (
            32,
            34,
            37,
            255,
        )

        self.hover_background: tuple[int, int, int, int] = (
            40,
            42,
            46,
            255,
        )

        self.focus_background: tuple[int, int, int, int] = (
            38,
            40,
            44,
            255,
        )

        self.border_color: tuple[int, int, int, int] = (
            80,
            80,
            85,
            255,
        )

        self.focus_border_color: tuple[int, int, int, int] = (
            80,
            140,
            220,
            255,
        )

        self.placeholder_color: tuple[int, int, int, int] = (
            130,
            130,
            135,
            255,
        )

        self.text_color: tuple[int, int, int, int] = (
            235,
            235,
            235,
            255,
        )

        self.cursor_color: tuple[int, int, int, int] = (
            235,
            235,
            235,
            255,
        )

        self.border_width: float = 2.0
        self.border_radius: float = 6.0

        self.padding: float = 10.0

        # ----------------------------------------------------------
        # Callbacks
        # ----------------------------------------------------------

        self.on_change: Callable[[str], None] | None = None
        self.on_submit: Callable[[str], None] | None = None

        # ----------------------------------------------------------
        # Child nodes
        # ----------------------------------------------------------

        self.panel = self.create_child(
            "Panel",
            node_type=Panel,
        )

        self.label = self.create_child(
            "Label",
            node_type=Label,
        )

        self.cursor = self.create_child(
            "Cursor",
            node_type=Panel,
        )

        self._sync_layout()
        self._sync_visuals()

    # ==============================================================
    # Content
    # ==============================================================

    def set_text(
        self,
        text: str,
        *,
        emit: bool = True,
    ) -> None:
        text = str(text)

        if self.max_length > 0:
            text = text[:self.max_length]

        if text == self.text:
            return

        self.text = text

        self.cursor_position = min(
            self.cursor_position,
            len(self.text),
        )

        if emit:
            callback = self.on_change

            if callback is not None:
                callback(self.text)

        self._sync_layout()
        self._sync_visuals()

    def clear(self) -> None:
        self.set_text("")

    # ==============================================================
    # Focus
    # ==============================================================

    def on_focus(self) -> None:
        """
        Called by UINode/UIRoot when this TextInput receives focus.
        """

        self.cursor_position = len(
            self.text
        )

        self._sync_layout()
        self._sync_visuals()

    def on_blur(self) -> None:
        """
        Called by UINode/UIRoot when this TextInput loses focus.
        """

        self.pressed = False

        self._sync_visuals()

    # ==============================================================
    # Display
    # ==============================================================

    @property
    def displayed_text(self) -> str:
        if self.text:
            return self.text

        return self.placeholder

    @property
    def content_size(self) -> tuple[float, float]:
        text_width = max(
            0.0,
            len(self.displayed_text)
            * 16.0
            * self.text_scale,
        )

        text_height = (
            32.0
            * self.text_scale
        )

        return (
            max(
                160.0,
                text_width
                + self.padding * 2.0,
            ),
            max(
                40.0,
                text_height
                + self.padding * 2.0,
            ),
        )

    # ==============================================================
    # Layout
    # ==============================================================

    def _sync_layout(self) -> None:
        self.size = self.content_size

        width, height = self.size

        # ----------------------------------------------------------
        # Background panel
        # ----------------------------------------------------------

        self.panel.size = (
            width,
            height,
        )

        self.panel.anchor = (
            0.5,
            0.5,
        )

        self.panel.pivot = (
            0.5,
            0.5,
        )

        self.panel.position = (
            0.0,
            0.0,
        )

        # ----------------------------------------------------------
        # Text
        # ----------------------------------------------------------

        self.label.text = self.displayed_text
        self.label.scale = self.text_scale

        self.label.anchor = (
            0.0,
            0.5,
        )

        self.label.pivot = (
            0.0,
            0.5,
        )

        self.label.position = (
            self.padding,
            0.0,
        )

        # ----------------------------------------------------------
        # Cursor
        # ----------------------------------------------------------

        self.cursor.size = (
            2.0,
            height - self.padding * 2.0,
        )

        self.cursor.anchor = (
            0.0,
            0.5,
        )

        self.cursor.pivot = (
            0.0,
            0.5,
        )

        cursor_x = (
            self.padding
            + self.cursor_position
            * 16.0
            * self.text_scale
        )

        self.cursor.position = (
            cursor_x,
            0.0,
        )

    # ==============================================================
    # Visuals
    # ==============================================================

    def _sync_visuals(self) -> None:
        if self.focused:
            self.panel.background = (
                self.focus_background
            )

            self.panel.border_color = (
                self.focus_border_color
            )

        elif self.hovered:
            self.panel.background = (
                self.hover_background
            )

            self.panel.border_color = (
                self.border_color
            )

        else:
            self.panel.background = (
                self.background
            )

            self.panel.border_color = (
                self.border_color
            )

        self.panel.border_width = (
            self.border_width
        )

        self.panel.border_radius = (
            self.border_radius
        )

        if self.text:
            self.label.color = (
                self.text_color
            )

        else:
            self.label.color = (
                self.placeholder_color
            )

        self.cursor.background = (
            self.cursor_color
        )

        self.cursor.border_width = 0.0
        self.cursor.border_radius = 0.0

        self.cursor.visible = (
            self.focused
        )

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
            self.hovered = False
            self.pressed = False

            self._sync_visuals()

            return

        mouse_x, mouse_y = (
            ui_input.mouse_position
        )

        self.hovered = self.contains_point(
            mouse_x,
            mouse_y,
        )

        # ----------------------------------------------------------
        # Mouse
        # ----------------------------------------------------------

        if ui_input.mouse_left_pressed:
            self.pressed = (
                self.hovered
            )

        if ui_input.mouse_left_released:
            self.pressed = False

        # ----------------------------------------------------------
        # Keyboard / text input
        # ----------------------------------------------------------

        if self.focused:
            for text in ui_input.text_input:
                self._insert_text(
                    text
                )

            if ui_input.key_pressed(
                sdl3.SDL_SCANCODE_BACKSPACE
            ):
                self._backspace()

            if ui_input.key_pressed(
                sdl3.SDL_SCANCODE_DELETE
            ):
                self._delete()

            if ui_input.key_pressed(
                sdl3.SDL_SCANCODE_LEFT
            ):
                self.cursor_position = max(
                    0,
                    self.cursor_position - 1,
                )

            if ui_input.key_pressed(
                sdl3.SDL_SCANCODE_RIGHT
            ):
                self.cursor_position = min(
                    len(self.text),
                    self.cursor_position + 1,
                )

            if ui_input.key_pressed(
                sdl3.SDL_SCANCODE_HOME
            ):
                self.cursor_position = 0

            if ui_input.key_pressed(
                sdl3.SDL_SCANCODE_END
            ):
                self.cursor_position = len(
                    self.text
                )

            if ui_input.key_pressed(
                sdl3.SDL_SCANCODE_RETURN
            ):
                callback = self.on_submit

                if callback is not None:
                    callback(
                        self.text
                    )

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

        self.panel.render(
            renderer
        )

        self.label.render(
            renderer
        )

        self.cursor.render(
            renderer
        )

    # ==============================================================
    # Text editing
    # ==============================================================

    def _insert_text(
        self,
        text: str,
    ) -> None:
        if not text:
            return

        if self.max_length > 0:
            available = (
                self.max_length
                - len(self.text)
            )

            if available <= 0:
                return

            text = text[:available]

        if not text:
            return

        self.text = (
            self.text[:self.cursor_position]
            + text
            + self.text[self.cursor_position:]
        )

        self.cursor_position += len(
            text
        )

        callback = self.on_change

        if callback is not None:
            callback(
                self.text
            )

    def _backspace(self) -> None:
        if self.cursor_position <= 0:
            return

        self.text = (
            self.text[:self.cursor_position - 1]
            + self.text[self.cursor_position:]
        )

        self.cursor_position -= 1

        callback = self.on_change

        if callback is not None:
            callback(
                self.text
            )

    def _delete(self) -> None:
        if self.cursor_position >= len(
            self.text
        ):
            return

        self.text = (
            self.text[:self.cursor_position]
            + self.text[self.cursor_position + 1:]
        )

        callback = self.on_change

        if callback is not None:
            callback(
                self.text
            )