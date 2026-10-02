"""Shared scene mechanics for Nexora's standalone editors.

This module deliberately owns only editor-shell behaviour: modal state,
project-scoped file-browser plumbing, exclusive menus and renderer-backed
control dispatch. Domain-specific document operations stay in each editor.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from nexora.scene import Scene

from .browser import FileBrowserModel, sync_browser_list
from .layout import close_other_menus
from .widgets import Menu, TextField, UITheme


class StandaloneEditorScene(Scene):
    """Common shell for renderer-backed standalone editor scenes."""

    CONTROL_STOP_ON_HANDLED = False
    CONTROL_MANAGE_TEXT_FOCUS = True
    MODAL_CLOSE_STATUS: str | None = None

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.theme = UITheme()
        self.modal: str | None = None
        self.browser_mode = ""
        self.browser_root = Path.cwd().resolve()
        self.browser_path = self.browser_root
        self.browser_entries: list[Path] = []
        self.file_browser = FileBrowserModel()
        self.info_title = ""
        self.info_lines: tuple[str, ...] = ()
        self.menus: list[Menu] = []

    # ------------------------------------------------------------------
    # Project asset paths
    # ------------------------------------------------------------------

    def _asset_root(self) -> Path:
        return self.project_context.assets_root

    def _asset_relative(self, path: Path) -> str:
        return self.project_context.relative_asset(path, root=self._asset_root())

    def _asset_path(self, value: str | Path) -> Path:
        return self.project_context.resolve_asset(value)

    # ------------------------------------------------------------------
    # Browser plumbing
    # ------------------------------------------------------------------

    def _open_file_browser(
        self,
        mode: str,
        *,
        root: str | Path,
        start: str | Path | None = None,
        extensions: Iterable[str] = (),
        filename: str | None = None,
    ) -> None:
        self.modal = "browser"
        self.browser_mode = str(mode)
        self.browser_root = Path(root).expanduser().resolve()
        self.file_browser.open(
            self.browser_root,
            start=start,
            extensions=extensions,
        )
        if filename is not None and hasattr(self, "browser_name"):
            self.browser_name.set_text(filename)
        self._refresh_browser()

    def _refresh_browser(self) -> None:
        self.file_browser.refresh()
        self.browser_path = self.file_browser.path
        self.browser_entries = list(self.file_browser.entries)
        browser_list = getattr(self, "browser_list", None)
        if browser_list is not None:
            sync_browser_list(self.file_browser, browser_list)

    def _select_browser_entry(self, index: int) -> Path | None:
        path = self.file_browser.select(index)
        self._refresh_browser()
        return path

    # ------------------------------------------------------------------
    # Menus and modals
    # ------------------------------------------------------------------

    def _set_menus(self, menus: Sequence[Menu]) -> None:
        self.menus = list(menus)
        for menu in self.menus:
            menu.on_open = self._menu_opened

    def _menu_opened(self, opened: Menu) -> None:
        close_other_menus(self.menus, opened)

    def _open_info_dialog(self, title: str, lines: Sequence[str]) -> None:
        self.info_title = str(title)
        self.info_lines = tuple(str(line) for line in lines)
        self.modal = "info"

    def _close_modal(self) -> None:
        self.modal = None
        if self.MODAL_CLOSE_STATUS is not None and hasattr(self, "status"):
            self.status = self.MODAL_CLOSE_STATUS

    # ------------------------------------------------------------------
    # Shared control dispatch
    # ------------------------------------------------------------------

    def _focus_fields(
        self,
        fields: Sequence[TextField],
        input_manager,
        mouse_x: float,
        mouse_y: float,
    ) -> None:
        if not input_manager.mouse_pressed("left"):
            return
        clicked = next(
            (
                field
                for field in fields
                if getattr(field, "visible", True)
                and field.rect.contains(mouse_x, mouse_y)
            ),
            None,
        )
        for field in fields:
            if field is not clicked:
                field.blur(input_manager)

    def _update_controls(self, controls: Sequence, *args) -> None:
        """Update controls while supporting the existing editor call shapes.

        Item Editor calls ``(controls, mouse_x, mouse_y)`` while the other
        standalone editors pass ``(controls, input_manager, mouse_x, mouse_y)``.
        Keeping both forms avoids churn in domain-specific update loops.
        """

        if len(args) == 2:
            input_manager = self.game.input
            mouse_x, mouse_y = args
        elif len(args) == 3:
            input_manager, mouse_x, mouse_y = args
        else:
            raise TypeError(
                "_update_controls expects (controls, mouse_x, mouse_y) or "
                "(controls, input_manager, mouse_x, mouse_y)."
            )

        controls = list(controls)
        if self.CONTROL_MANAGE_TEXT_FOCUS:
            fields = [control for control in controls if isinstance(control, TextField)]
            self._focus_fields(fields, input_manager, float(mouse_x), float(mouse_y))

        for control in controls:
            handled = control.update(input_manager, mouse_x, mouse_y)
            if handled and self.CONTROL_STOP_ON_HANDLED:
                break


__all__ = ["StandaloneEditorScene"]
