"""Single shared file-dialog implementation for standalone Nexora editors."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from .browser import FileBrowserModel, sync_browser_list
from .dialogs import layout_file_browser_dialog, render_file_browser_dialog
from .widgets import Button, ListBox, Rect, TextField, UITheme


class FileDialog:
    """Own browser state, widgets, geometry, update controls and rendering.

    Editors provide only mode/title/extensions and domain-specific callbacks.
    Navigation, filename editing and visual layout are intentionally implemented
    once here so standalone editors cannot drift apart.
    """

    def __init__(
        self,
        *,
        on_selected: Callable[[int], None],
        on_cancel: Callable[[], None],
        on_action: Callable[[], None],
    ) -> None:
        self.model = FileBrowserModel()
        self.mode = ""
        self.root = Path.cwd().resolve()
        self.path = self.root
        self.entries: list[Path] = []
        self.list_box = ListBox(Rect(0, 0, 1, 1), on_selected)
        self.name_field = TextField(Rect(0, 0, 1, 1), "", "File name")
        self.cancel_button = Button(Rect(0, 0, 1, 1), "Cancel", on_cancel)
        self.action_button = Button(Rect(0, 0, 1, 1), "Save", on_action)
        self.show_filename = False

    def open(
        self,
        mode: str,
        *,
        root: str | Path,
        start: str | Path | None = None,
        extensions: Iterable[str] = (),
        filename: str | None = None,
        show_filename: bool = False,
        action_text: str = "Save",
    ) -> None:
        self.mode = str(mode)
        self.root = Path(root).expanduser().resolve()
        self.show_filename = bool(show_filename)
        self.name_field.visible = self.show_filename
        self.action_button.visible = self.show_filename
        self.action_button.text = str(action_text)
        self.model.open(self.root, start=start, extensions=extensions)
        if filename is not None:
            self.name_field.set_text(filename)
        self.refresh()

    def refresh(self) -> None:
        self.model.refresh()
        self.path = self.model.path
        self.entries = list(self.model.entries)
        sync_browser_list(self.model, self.list_box)

    def select(self, index: int) -> Path | None:
        path = self.model.select(index)
        self.refresh()
        return path

    def controls(self) -> list:
        controls = [self.list_box, self.cancel_button]
        if self.show_filename:
            controls.extend((self.name_field, self.action_button))
        return controls

    def layout(
        self,
        viewport: tuple[float, float],
        *,
        margin_x: float = 150.0,
        margin_y: float = 76.0,
    ) -> None:
        layout_file_browser_dialog(
            viewport,
            list_box=self.list_box,
            cancel_button=self.cancel_button,
            name_field=self.name_field,
            action_button=self.action_button,
            show_filename=self.show_filename,
            margin_x=margin_x,
            margin_y=margin_y,
        )

    def render(
        self,
        renderer,
        viewport: tuple[float, float],
        theme: UITheme,
        *,
        title: str,
        margin_x: float = 150.0,
        margin_y: float = 76.0,
    ) -> None:
        render_file_browser_dialog(
            renderer,
            viewport,
            theme,
            title=title,
            path=self.path,
            list_box=self.list_box,
            cancel_button=self.cancel_button,
            name_field=self.name_field,
            action_button=self.action_button,
            show_filename=self.show_filename,
            margin_x=margin_x,
            margin_y=margin_y,
        )


__all__ = ["FileDialog"]
