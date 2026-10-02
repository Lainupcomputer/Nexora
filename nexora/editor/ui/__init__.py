"""Shared renderer-backed UI primitives used by standalone editors.

The standalone tilemap, item and cutscene editors all use the same small
widget toolkit.  Keeping the public surface here gives editor code one stable
import path and keeps the implementation details in :mod:`widgets`.
"""

from .widgets import (
    Button,
    CategorizedListBox,
    CheckBox,
    Control,
    Dropdown,
    ListBox,
    Menu,
    Rect,
    TextField,
    UITheme,
    draw_outline,
    draw_rect,
    draw_text,
    rgba,
)
from .browser import FileBrowserModel, sync_browser_list
from .layout import (
    FormLayout,
    centered_rect,
    close_other_menus,
    layout_equal_row,
    layout_fixed_row,
)
from .dialogs import browser_window, render_file_browser_dialog, render_info_dialog
from .scene import StandaloneEditorScene
from .render import (
    render_document_title,
    render_editor_shell,
    render_form_label,
    render_section_title,
    render_status_bar,
)

__all__ = [
    "Button",
    "CategorizedListBox",
    "CheckBox",
    "Control",
    "Dropdown",
    "ListBox",
    "Menu",
    "Rect",
    "TextField",
    "UITheme",
    "draw_outline",
    "draw_rect",
    "draw_text",
    "rgba",
    "FileBrowserModel",
    "FormLayout",
    "sync_browser_list",
    "centered_rect",
    "close_other_menus",
    "layout_equal_row",
    "layout_fixed_row",
    "browser_window",
    "render_file_browser_dialog",
    "render_info_dialog",
    "render_document_title",
    "render_editor_shell",
    "render_form_label",
    "render_section_title",
    "render_status_bar",
    "StandaloneEditorScene",
]
