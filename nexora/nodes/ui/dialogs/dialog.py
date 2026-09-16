from __future__ import annotations

from collections.abc import Callable

import sdl3

from nexora.nodes.ui.ui_node import UINode
from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.controls.button import Button
from nexora.nodes.ui.output.label import Label
from nexora.signals import Signal


class Dialog(UINode):
    """Reusable modal dialog node.

    A Dialog is designed to be added directly below :class:`UIRoot`.
    While it is open, UIRoot restricts focus and input dispatch to the
    dialog subtree.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.width_mode = "fill"
        self.height_mode = "fill"
        self.anchor = (0.5, 0.5)
        self.pivot = (0.5, 0.5)

        self.dialog_size: tuple[float, float] = (520.0, 280.0)
        self.min_dialog_size: tuple[float, float] = (320.0, 180.0)
        self.margin: float = 24.0
        self.header_height: float = 52.0
        self.footer_height: float = 64.0
        self.content_padding: float = 18.0

        self.title: str = "Dialog"
        self.confirm_text: str = "OK"
        self.cancel_text: str = "Cancel"
        self.show_confirm_button: bool = True
        self.show_cancel_button: bool = True
        self.close_on_confirm: bool = True
        self.close_on_cancel: bool = True
        self.escape_closes: bool = True
        self.enter_confirms: bool = True

        self.backdrop_color = (0, 0, 0, 155)
        self.window_background = (28, 30, 34, 255)
        self.window_border_color = (70, 74, 82, 255)
        self.header_background = (34, 37, 42, 255)
        self.footer_background = (31, 33, 37, 255)

        self.on_confirm: Callable[[], None] | None = None
        self.on_cancel: Callable[[], None] | None = None

        self.opened = Signal(f"{name}.opened", owner=self)
        self.closed = Signal(f"{name}.closed", owner=self)
        self.confirmed = Signal(f"{name}.confirmed", owner=self)
        self.cancelled = Signal(f"{name}.cancelled", owner=self)

        self.backdrop = self.create_child("Backdrop", node_type=Panel)
        self.backdrop.anchor = (0.5, 0.5)
        self.backdrop.pivot = (0.5, 0.5)
        self.backdrop.background = self.backdrop_color
        self.backdrop.border_width = 0.0

        self.window = self.create_child("Window", node_type=Panel)
        self.window.anchor = (0.5, 0.5)
        self.window.pivot = (0.5, 0.5)
        self.window.background = self.window_background
        self.window.border_color = self.window_border_color
        self.window.border_width = 1.0
        self.window.border_radius = 8.0

        self.header = self.window.create_child("Header", node_type=Panel)
        self.header.anchor = (0.5, 0.0)
        self.header.pivot = (0.5, 0.5)
        self.header.background = self.header_background
        self.header.border_width = 0.0

        self.title_label = self.header.create_child("Title", node_type=Label)
        self.title_label.anchor = (0.0, 0.5)
        self.title_label.pivot = (0.0, 0.5)
        self.title_label.scale = 1.0

        self.content = self.window.create_child("Content", node_type=Panel)
        self.content.anchor = (0.5, 0.5)
        self.content.pivot = (0.5, 0.5)
        self.content.background = (0, 0, 0, 0)
        self.content.border_width = 0.0

        self.footer = self.window.create_child("Footer", node_type=Panel)
        self.footer.anchor = (0.5, 1.0)
        self.footer.pivot = (0.5, 0.5)
        self.footer.background = self.footer_background
        self.footer.border_width = 0.0

        self.cancel_button = self.footer.create_child("Cancel", node_type=Button)
        self.cancel_button.size = (110.0, 38.0)
        self.cancel_button.on_click = self.cancel

        self.confirm_button = self.footer.create_child("Confirm", node_type=Button)
        self.confirm_button.size = (110.0, 38.0)
        self.confirm_button.on_click = self.confirm

        self._previous_focus: UINode | None = None
        self._is_open = False
        self.visible = False
        self.enabled = False

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open(self, *, focus: UINode | None = None) -> Dialog:
        if self._is_open:
            return self

        root = self.ui_root
        self._previous_focus = getattr(root, "focused_node", None)
        self._is_open = True
        self.visible = True
        self.enabled = True
        self._sync_layout()

        if root is not None:
            push_modal = getattr(root, "push_modal", None)
            if push_modal is not None:
                push_modal(self)

        target = focus
        if target is None and self.show_confirm_button:
            target = self.confirm_button
        if target is None and self.show_cancel_button:
            target = self.cancel_button
        if target is not None:
            target.focus()

        self.opened.emit(self)
        return self

    def close(self) -> Dialog:
        if not self._is_open:
            return self

        root = self.ui_root
        self._is_open = False
        self.visible = False
        self.enabled = False

        if root is not None:
            pop_modal = getattr(root, "pop_modal", None)
            if pop_modal is not None:
                pop_modal(self)

            previous = self._previous_focus
            if previous is not None and previous.can_focus:
                root.set_focus(previous)
            elif getattr(root, "focused_node", None) is not None:
                root.clear_focus()

        self._previous_focus = None
        self.closed.emit(self)
        return self

    def confirm(self) -> None:
        if not self._is_open:
            return

        callback = self.on_confirm
        if callback is not None:
            callback()

        self.confirmed.emit(self)
        if self.close_on_confirm:
            self.close()

    def cancel(self) -> None:
        if not self._is_open:
            return

        callback = self.on_cancel
        if callback is not None:
            callback()

        self.cancelled.emit(self)
        if self.close_on_cancel:
            self.close()

    def _sync_layout(self) -> None:
        viewport_w = max(0.0, self._viewport_width)
        viewport_h = max(0.0, self._viewport_height)
        self.size = (viewport_w, viewport_h)
        self.backdrop.size = self.size

        max_w = max(self.min_dialog_size[0], viewport_w - self.margin * 2.0)
        max_h = max(self.min_dialog_size[1], viewport_h - self.margin * 2.0)
        width = min(max(self.dialog_size[0], self.min_dialog_size[0]), max_w)
        height = min(max(self.dialog_size[1], self.min_dialog_size[1]), max_h)
        self.window.size = (width, height)

        header_h = min(self.header_height, height)
        footer_h = min(self.footer_height, max(0.0, height - header_h))
        content_h = max(0.0, height - header_h - footer_h)

        self.header.size = (width - 2.0, header_h)
        self.header.position = (0.0, header_h / 2.0)
        self.title_label.position = (self.content_padding, 0.0)
        self.title_label.text = self.title

        self.content.size = (
            max(0.0, width - self.content_padding * 2.0),
            max(0.0, content_h - self.content_padding * 2.0),
        )
        self.content.position = (0.0, (header_h - footer_h) / 2.0)

        self.footer.size = (width - 2.0, footer_h)
        self.footer.position = (0.0, -footer_h / 2.0)

        self.cancel_button.visible = self.show_cancel_button
        self.cancel_button.enabled = self.show_cancel_button
        self.confirm_button.visible = self.show_confirm_button
        self.confirm_button.enabled = self.show_confirm_button
        self.cancel_button.text = self.cancel_text
        self.confirm_button.text = self.confirm_text

        gap = 10.0
        right = width / 2.0 - self.content_padding
        if self.show_confirm_button:
            self.confirm_button.anchor = (0.5, 0.5)
            self.confirm_button.pivot = (0.5, 0.5)
            self.confirm_button.position = (right - self.confirm_button.size[0] / 2.0, 0.0)
            right -= self.confirm_button.size[0] + gap
        if self.show_cancel_button:
            self.cancel_button.anchor = (0.5, 0.5)
            self.cancel_button.pivot = (0.5, 0.5)
            self.cancel_button.position = (right - self.cancel_button.size[0] / 2.0, 0.0)

    def update_input(self, ui_input) -> None:
        if not self._is_open:
            return

        self._sync_layout()

        if self.escape_closes and ui_input.key_pressed(sdl3.SDL_SCANCODE_ESCAPE):
            self.cancel()
            return

        if self.enter_confirms and (
            ui_input.key_pressed(sdl3.SDL_SCANCODE_RETURN)
            or ui_input.key_pressed(sdl3.SDL_SCANCODE_KP_ENTER)
        ):
            self.confirm()
            return

        super().update_input(ui_input)

    def render(self, renderer) -> None:
        if not self._is_open:
            return
        self._sync_layout()
        super().render(renderer)
