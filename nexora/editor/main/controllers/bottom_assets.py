from __future__ import annotations

from nexora.editor.main.asset_browser import AssetPreview
from nexora.nodes import Label, ListView, Panel, TextInput


class BottomAssetsPanel:
    """Owns the Assets tab UI and layout inside the main editor bottom dock."""

    def __init__(self, editor) -> None:
        self.editor = editor

    def build(self) -> None:
        e = self.editor
        e.asset_up_button = e._button(
            e.bottom_dock,
            "AssetUpButton",
            "Up",
            e._asset_go_up,
        )
        e.asset_refresh_button = e._button(
            e.bottom_dock,
            "AssetRefreshButton",
            "Refresh",
            e._refresh_asset_browser,
        )

        e.asset_search = e.bottom_dock.create_child(
            "AssetSearch",
            node_type=TextInput,
        )
        e.asset_search.placeholder = "Search assets..."
        e.asset_search.text_scale = 0.62
        e.asset_search.auto_size = False
        e.asset_search.on_change = e._on_asset_search_changed

        e.asset_path_label = e.bottom_dock.create_child(
            "AssetPath",
            node_type=Label,
        )
        e.asset_path_label.scale = 0.58
        e.asset_path_label.anchor = (0.0, 0.0)
        e.asset_path_label.pivot = (0.0, 0.0)

        e.asset_list = e.bottom_dock.create_child(
            "AssetList",
            node_type=ListView,
        )
        e.asset_list.item_height = 28.0
        e.asset_list.spacing = 1.0
        e.asset_list.padding_left = 5.0
        e.asset_list.padding_right = 5.0
        e.asset_list.padding_top = 5.0
        e.asset_list.padding_bottom = 5.0
        e.asset_list.text_padding_left = 7.0
        e.asset_list.text_scale = 0.58
        e.asset_list.on_change = e._on_asset_selected
        e.asset_list.on_activate = e._on_asset_activated

        e.asset_preview = e.bottom_dock.create_child(
            "AssetPreview",
            node_type=AssetPreview,
        )
        if e.game.engine is not None:
            e.asset_preview.asset_manager = e.game.engine.assets

        e.asset_details = e.bottom_dock.create_child(
            "AssetDetails",
            node_type=Label,
        )
        e.asset_details.scale = 0.55
        e.asset_details.anchor = (0.0, 0.0)
        e.asset_details.pivot = (0.0, 0.0)

        e.asset_context = e.bottom_dock.create_child(
            "AssetContextMenu",
            node_type=Panel,
        )
        e.asset_context.background = (28, 30, 34, 255)
        e.asset_context.border_color = (70, 74, 80, 255)
        e.asset_context.border_width = 1.0
        e.asset_context.visible = False

        e.asset_context_open = e._button(
            e.asset_context,
            "ContextOpen",
            "Open",
            e._asset_context_open_selected,
        )
        e.asset_context_reveal = e._button(
            e.asset_context,
            "ContextReveal",
            "Reveal",
            e._asset_context_reveal_selected,
        )
        e.asset_context_refresh = e._button(
            e.asset_context,
            "ContextRefresh",
            "Refresh",
            e._refresh_asset_browser,
        )

    def set_visible(self, visible: bool) -> None:
        e = self.editor
        for node in (
            e.asset_up_button,
            e.asset_refresh_button,
            e.asset_search,
            e.asset_path_label,
            e.asset_list,
            e.asset_preview,
            e.asset_details,
        ):
            node.visible = visible

        if not visible:
            e.asset_context.visible = False

    def sync_layout(self, width: float, height: float) -> None:
        e = self.editor
        toolbar_y = 49.0

        e.asset_up_button.size = (54.0, 28.0)
        e.asset_up_button.anchor = (0.0, 0.0)
        e.asset_up_button.pivot = (0.5, 0.5)
        e.asset_up_button.position = (37.0, toolbar_y)

        e.asset_refresh_button.size = (78.0, 28.0)
        e.asset_refresh_button.anchor = (0.0, 0.0)
        e.asset_refresh_button.pivot = (0.5, 0.5)
        e.asset_refresh_button.position = (108.0, toolbar_y)

        search_w = min(280.0, max(160.0, width * 0.22))
        e.asset_search.size = (search_w, 30.0)
        e.asset_search.anchor = (0.0, 0.0)
        e.asset_search.pivot = (0.5, 0.5)
        e.asset_search.position = (164.0 + search_w / 2.0, toolbar_y)

        e.asset_path_label.position = (175.0 + search_w, 39.0)

        content_top = 70.0
        content_bottom_margin = 8.0
        content_h = max(0.0, height - content_top - content_bottom_margin)
        preview_w = min(150.0, max(110.0, width * 0.12))
        details_w = min(245.0, max(180.0, width * 0.19))
        right_margin = 8.0
        gap = 8.0
        list_w = max(
            180.0,
            width - preview_w - details_w - right_margin - gap * 3.0,
        )

        e.asset_list.size = (list_w, content_h)
        e.asset_list.anchor = (0.0, 0.0)
        e.asset_list.pivot = (0.5, 0.5)
        e.asset_list.position = (
            8.0 + list_w / 2.0,
            content_top + content_h / 2.0,
        )

        preview_x = 8.0 + list_w + gap
        e.asset_preview.size = (preview_w, content_h)
        e.asset_preview.anchor = (0.0, 0.0)
        e.asset_preview.pivot = (0.5, 0.5)
        e.asset_preview.position = (
            preview_x + preview_w / 2.0,
            content_top + content_h / 2.0,
        )

        details_x = preview_x + preview_w + gap
        e.asset_details.position = (details_x, content_top + 5.0)

        context_w = 96.0
        context_h = 102.0
        e.asset_context.size = (context_w, context_h)
        e.asset_context.anchor = (0.0, 0.0)
        e.asset_context.pivot = (0.5, 0.5)
        e.asset_context.position = (
            max(context_w / 2.0 + 8.0, list_w - context_w / 2.0),
            content_top + context_h / 2.0 + 4.0,
        )

        for index, button in enumerate(
            (
                e.asset_context_open,
                e.asset_context_reveal,
                e.asset_context_refresh,
            )
        ):
            button.size = (82.0, 26.0)
            button.anchor = (0.5, 0.0)
            button.pivot = (0.5, 0.5)
            button.position = (0.0, 18.0 + index * 31.0)
