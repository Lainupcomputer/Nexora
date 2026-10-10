"""Shared scene mechanics for Nexora editor modes.

This module deliberately owns only editor-shell behaviour: modal state,
project-scoped file-browser plumbing, exclusive menus and renderer-backed
control dispatch. Domain-specific document operations stay in each editor.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from nexora.scene import Scene

from .ui.dialogs import render_info_dialog
from .ui.file_dialog import FileDialog
from .ui.layout import close_other_menus
from .ui.widgets import Menu, TextField, UITheme


class EditorBaseScene(Scene):
    """Shared base scene for every Nexora editor except the Project Hub.

    The Main Editor defines the visual language; specialized editors reuse the
    same theme, toolbar/status dimensions and common editor mechanics.
    """

    TOOLBAR_HEIGHT = 48.0
    STATUS_HEIGHT = 26.0
    CONTROL_STOP_ON_HANDLED = False
    CONTROL_MANAGE_TEXT_FOCUS = True
    MODAL_CLOSE_STATUS: str | None = None

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.theme = UITheme()
        self.modal: str | None = None
        self.file_dialog = FileDialog(
            on_selected=self._browser_selected,
            on_cancel=self._close_modal,
            on_action=self._browser_action,
        )
        # Compatibility aliases retained while standalone editors migrate to
        # the shared dialog API. They all reference the same implementation.
        self.file_browser = self.file_dialog.model
        self.browser_list = self.file_dialog.list_box
        self.browser_name = self.file_dialog.name_field
        self.browser_cancel_button = self.file_dialog.cancel_button
        self.browser_save_button = self.file_dialog.action_button
        self.browser_action_button = self.file_dialog.action_button
        self.browser_mode = ""
        self.browser_root = Path.cwd().resolve()
        self.browser_path = self.browser_root
        self.browser_entries: list[Path] = []
        self.info_title = ""
        self.info_lines: tuple[str, ...] = ()
        self.menus: list[Menu] = []

    # ------------------------------------------------------------------
    # Project asset paths
    # ------------------------------------------------------------------

    def _asset_reference(self) -> str | Path | None:
        """Reference used to select the active asset root for this editor."""
        return None

    def _asset_root(self) -> Path:
        return self.project_context.asset_root_for(self._asset_reference())

    def _asset_relative(self, path: str | Path) -> str:
        return self.project_context.relative_asset(path, root=self._asset_root())

    def _asset_path(self, value: str | Path) -> Path:
        return self.project_context.resolve_asset(
            value,
            reference=self._asset_reference(),
        )

    def _project_file_path(
        self,
        value: str | Path,
        *,
        roots: Iterable[str | Path] = (),
        include_assets: bool = False,
    ) -> Path:
        return self.project_context.resolve_project_file(
            value,
            roots=roots,
            include_assets=include_assets,
            reference=self._asset_reference(),
        )

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
        show_filename: bool | None = None,
        action_text: str = "Save",
    ) -> None:
        self.modal = "browser"
        self.browser_mode = str(mode)
        self.file_dialog.open(
            mode,
            root=root,
            start=start,
            extensions=extensions,
            filename=filename,
            show_filename=(mode in {"save", "map_save"}) if show_filename is None else show_filename,
            action_text=action_text,
        )
        self._sync_file_dialog_state()

    def _sync_file_dialog_state(self) -> None:
        self.browser_mode = self.file_dialog.mode
        self.browser_root = self.file_dialog.root
        self.browser_path = self.file_dialog.path
        self.browser_entries = list(self.file_dialog.entries)

    def _refresh_browser(self) -> None:
        self.file_dialog.refresh()
        self._sync_file_dialog_state()

    def _select_browser_entry(self, index: int) -> Path | None:
        path = self.file_dialog.select(index)
        self._sync_file_dialog_state()
        return path

    def _layout_file_dialog(
        self,
        viewport: tuple[float, float],
        *,
        margin_x: float = 150.0,
        margin_y: float = 76.0,
    ) -> None:
        self.file_dialog.layout(
            viewport,
            margin_x=margin_x,
            margin_y=margin_y,
        )

    def _file_dialog_controls(self) -> list:
        return self.file_dialog.controls()

    def _render_file_dialog(
        self,
        renderer,
        viewport: tuple[float, float],
        *,
        title: str,
        margin_x: float = 150.0,
        margin_y: float = 76.0,
    ) -> None:
        self.file_dialog.render(
            renderer,
            viewport,
            self.theme,
            title=title,
            margin_x=margin_x,
            margin_y=margin_y,
        )

    def _browser_selected(self, index: int) -> None:
        del index

    def _browser_action(self) -> None:
        pass

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


    def _render_info_dialog(
        self,
        renderer,
        viewport: tuple[float, float],
        *,
        width: float = 660.0,
        height: float = 340.0,
        line_step: float = 38.0,
    ) -> None:
        render_info_dialog(
            renderer,
            viewport,
            self.theme,
            title=self.info_title,
            lines=self.info_lines,
            close_button=self.info_close_button,
            width=width,
            height=height,
            line_step=line_step,
        )

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
        editors pass ``(controls, input_manager, mouse_x, mouse_y)``.
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


__all__ = ["EditorBaseScene"]
