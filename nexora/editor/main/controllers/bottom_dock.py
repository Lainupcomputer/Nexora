from __future__ import annotations

from nexora.nodes import Label

from .bottom_animation import BottomAnimationPanel
from .bottom_assets import BottomAssetsPanel
from .bottom_console import BottomConsolePanel


class BottomDockController:
    """Coordinates bottom-dock tabs and delegates each panel to its owner."""

    def __init__(self, editor) -> None:
        self.editor = editor
        if not hasattr(editor, "_bottom_tab"):
            editor._bottom_tab = "assets"
        self.assets_panel = BottomAssetsPanel(editor)
        self.console_panel = BottomConsolePanel(editor)
        self.animation_panel = BottomAnimationPanel(editor)

    def update(self) -> None:
        self.console_panel.update()

    def _build_bottom_dock(self) -> None:
        e = self.editor
        e.assets_button = e._button(
            e.bottom_dock,
            "AssetsTab",
            "Assets",
            lambda: self._set_bottom_tab("assets"),
        )
        e.console_button = e._button(
            e.bottom_dock,
            "ConsoleTab",
            "Console",
            lambda: self._set_bottom_tab("console"),
        )
        e.animation_button = e._button(
            e.bottom_dock,
            "AnimationTab",
            "Animation",
            lambda: self._set_bottom_tab("animation"),
        )

        e.bottom_title = e.bottom_dock.create_child(
            "BottomTitle",
            node_type=Label,
        )
        e.bottom_title.text = "Assets"
        e.bottom_title.scale = 0.78
        e.bottom_title.anchor = (0.0, 0.0)
        e.bottom_title.pivot = (0.0, 0.0)

        self.assets_panel.build()
        self.console_panel.build()
        self.animation_panel.build()

        # Do not refresh here yet: _build_bottom_dock() runs before the
        # status bar exists. _refresh_document_ui() performs the first asset
        # refresh after the complete editor UI has been created.
        self._apply_bottom_tab_visibility()

    def _apply_bottom_tab_visibility(self) -> None:
        tab = self.editor._bottom_tab
        self.assets_panel.set_visible(tab == "assets")
        self.console_panel.set_visible(tab == "console")
        self.animation_panel.set_visible(tab == "animation")

    def _set_bottom_tab(self, tab: str) -> None:
        e = self.editor
        if tab == "console":
            e._bottom_tab = "console"
            e.bottom_title.text = "Console"
            self._apply_bottom_tab_visibility()
            e.status_label.text = "Console panel selected"
            return

        if tab == "animation":
            e._bottom_tab = "animation"
            e.bottom_title.text = "Animation Editor"
            self._apply_bottom_tab_visibility()
            e._refresh_animation_panel()
            e.status_label.text = "Animation editor selected"
            return

        e._bottom_tab = "assets"
        e.bottom_title.text = "Assets"
        self._apply_bottom_tab_visibility()
        e._refresh_asset_browser()
        e.status_label.text = "Assets panel selected"

    def _refresh_console_output(self) -> None:
        self.console_panel.refresh_output()

    def _clear_editor_console(self) -> None:
        self.console_panel.clear()

    def _sync_bottom_layout(self, width: float, height: float) -> None:
        e = self.editor
        e.assets_button.size = (82.0, 32.0)
        e.assets_button.anchor = (0.0, 0.0)
        e.assets_button.pivot = (0.5, 0.5)
        e.assets_button.position = (51.0, 23.0)

        e.console_button.size = (92.0, 32.0)
        e.console_button.anchor = (0.0, 0.0)
        e.console_button.pivot = (0.5, 0.5)
        e.console_button.position = (144.0, 23.0)

        e.animation_button.size = (112.0, 32.0)
        e.animation_button.anchor = (0.0, 0.0)
        e.animation_button.pivot = (0.5, 0.5)
        e.animation_button.position = (245.0, 23.0)

        e.bottom_title.position = (490.0, 13.0)

        self.assets_panel.sync_layout(width, height)
        self.console_panel.sync_layout(width, height)
        self.animation_panel.sync_layout(width, height)
