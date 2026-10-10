from __future__ import annotations

from nexora.editor.commands import (
    AddNodeCommand,
    DeleteNodeCommand,
    RenameNodeCommand,
)
from nexora.nodes import ListView
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.tilemap import TileMap, TileProjection, TileSet


class SceneTreeController:
    """Scene-tree and node-editing behavior for :class:`EditorScene`."""

    def __init__(self, scene) -> None:
        self.scene = scene

    def build_scene_tree(self) -> None:
        scene = self.scene
        scene.scene_title = scene._panel_title(scene.scene_tree, "Scene")

        scene.add_node_button = scene._button(
            scene.scene_tree,
            "AddNodeButton",
            "+",
            self.open_add_node_dialog,
        )
        scene.rename_node_button = scene._button(
            scene.scene_tree,
            "RenameNodeButton",
            "Rename",
            self.open_rename_node_dialog,
        )
        scene.delete_node_button = scene._button(
            scene.scene_tree,
            "DeleteNodeButton",
            "Delete",
            self.request_delete_node,
        )

        scene.scene_list = scene.scene_tree.create_child(
            "SceneList",
            node_type=ListView,
        )
        scene.scene_list.item_height = 30.0
        scene.scene_list.spacing = 1.0
        scene.scene_list.padding_left = 6.0
        scene.scene_list.padding_right = 6.0
        scene.scene_list.padding_top = 6.0
        scene.scene_list.padding_bottom = 6.0
        scene.scene_list.text_padding_left = 8.0
        scene.scene_list.text_scale = 0.68
        scene.scene_list.on_change = self.on_scene_tree_selected

    def refresh_scene_tree(self) -> None:
        scene = self.scene
        selected = scene.selection.selected
        scene._scene_entries = list(scene.document.iter_tree_entries())
        scene.scene_list.set_items([entry.label for entry in scene._scene_entries])

        if selected is None:
            scene.scene_list.selected_index = -1
            return

        for index, entry in enumerate(scene._scene_entries):
            if entry.node is selected:
                scene.scene_list.set_selected_index(index, emit=False)
                break

    def on_scene_tree_selected(self, index: int, _label: str | None) -> None:
        scene = self.scene
        if not (0 <= index < len(scene._scene_entries)):
            scene.selection.clear()
            return
        scene.selection.select(scene._scene_entries[index].node)

    def on_add_node_type_selected(self, _index: int, label: str | None) -> None:
        if label:
            self.scene.add_node_name.set_text(str(label), emit=False)

    def editable_selected_node(self):
        scene = self.scene
        node = scene.selection.selected
        if node is None:
            return None
        if node is scene.document.scene.root or node is scene.document.scene.ui:
            return None
        return node

    def selected_parent_for_add(self):
        scene = self.scene
        selected = scene.selection.selected
        if selected is None:
            return scene.document.scene.root
        if getattr(selected, "world", None) is scene.document.scene.world:
            return selected
        return scene.document.scene.root

    def open_add_node_dialog(self) -> None:
        scene = self.scene
        parent = self.selected_parent_for_add()
        registry = scene.game.scene_serializer.registry
        type_ids = list(registry.registered_type_ids())
        if not type_ids:
            scene._show_error("No serializable node types are registered.")
            return

        scene.add_node_parent_label.text = f"Parent: {parent.name}"
        scene.add_node_type_list.set_items(type_ids)
        scene.add_node_type_list.set_selected_index(0, emit=False)
        scene.add_node_name.set_text(type_ids[0], emit=False)
        self.sync_add_node_dialog_layout()
        scene.add_node_dialog.open(focus=scene.add_node_name)

    def confirm_add_node(self) -> None:
        scene = self.scene
        index = scene.add_node_type_list.selected_index
        if not (0 <= index < len(scene.add_node_type_list.items)):
            return
        type_id = scene.add_node_type_list.items[index]
        name = scene.add_node_name.text.strip() or type_id
        parent = self.selected_parent_for_add()
        try:
            configure = (
                self.configure_default_tilemap_node
                if type_id == "TileMapNode"
                else None
            )
            command = AddNodeCommand(
                parent=parent,
                registry=scene.game.scene_serializer.registry,
                type_id=type_id,
                name=name,
                context=scene._serialization_context(),
                configure=configure,
            )
            node = scene.commands.execute(command)
        except Exception as exc:
            scene._show_error(f"Could not add node:\n{exc}")
            return

        scene.document.mark_dirty()
        scene.selection.select(node)
        scene._refresh_document_ui()
        scene.status_label.text = f"Added {name}"

    def configure_default_tilemap_node(self, node: TileMapNode) -> None:
        scene = self.scene
        candidates = (
            "demo_sprite.png",
            "world/isometric_tiles.png",
        )
        texture_asset = next(
            (
                candidate
                for candidate in candidates
                if scene.project_context.resolve_asset(candidate).is_file()
            ),
            None,
        )
        if texture_asset is None:
            raise FileNotFoundError(
                "No starter texture found in the project's assets folder."
            )

        tilemap = TileMap(
            name=f"{node.name}Map",
            width=16,
            height=16,
            tile_width=32,
            tile_height=32,
            projection=TileProjection.ANGLED_2D,
        )
        tilemap.create_layer("ground")

        if texture_asset == "demo_sprite.png":
            columns = rows = 3
        else:
            columns = rows = 1

        tileset = TileSet(
            name=f"{node.name}Tiles",
            columns=columns,
            rows=rows,
            tile_width=32,
            tile_height=32,
            texture_asset=texture_asset,
        )
        assets = scene.game.engine.assets
        texture = assets.texture(texture_asset)
        node.set_map(tilemap, tileset, texture)
        node.centered = True

    def open_rename_node_dialog(self) -> None:
        scene = self.scene
        node = self.editable_selected_node()
        if node is None:
            scene.status_label.text = "Select an editable node first"
            return
        scene.rename_node_name.set_text(str(node.name), emit=False)
        scene.rename_node_dialog.open(focus=scene.rename_node_name)

    def confirm_rename_node(self) -> None:
        scene = self.scene
        node = self.editable_selected_node()
        if node is None:
            return
        new_name = scene.rename_node_name.text.strip()
        if not new_name or new_name == str(node.name):
            return
        try:
            scene.commands.execute(RenameNodeCommand(node, new_name))
        except Exception as exc:
            scene._show_error(f"Could not rename node:\n{exc}")
            return
        scene._sync_prefab_instance_overrides(node)
        scene.document.mark_dirty()
        scene._refresh_document_ui()
        scene.status_label.text = f"Renamed node to {new_name}"

    def request_delete_node(self) -> None:
        scene = self.scene
        node = self.editable_selected_node()
        if node is None:
            scene.status_label.text = "Select an editable node first"
            return
        scene.delete_node_dialog.message = (
            f"Delete '{node.name}' and all of its children?"
        )
        scene.delete_node_dialog.open()

    def confirm_delete_node(self) -> None:
        scene = self.scene
        node = self.editable_selected_node()
        if node is None:
            return
        parent = node.parent
        name = str(node.name)
        try:
            command = DeleteNodeCommand(
                node=node,
                registry=scene.game.scene_serializer.registry,
                context=scene._serialization_context(),
            )
            scene.commands.execute(command)
        except Exception as exc:
            scene._show_error(f"Could not delete node:\n{exc}")
            return
        scene.selection.select(parent)
        scene.document.mark_dirty()
        scene._refresh_document_ui()
        scene.status_label.text = f"Deleted {name}"

    def undo(self) -> None:
        scene = self.scene
        if not scene.commands.can_undo:
            scene.status_label.text = "Nothing to undo"
            return
        label = scene.commands.undo_label or "command"
        result = scene.commands.undo()
        scene.document.mark_dirty()
        if result is not None:
            scene.selection.select(result)
        else:
            selected = scene.selection.selected
            if (
                selected is not None
                and not scene.document.scene.world.is_alive(selected.entity)
            ):
                scene.selection.clear()
        scene._sync_all_prefab_instance_overrides()
        scene._refresh_document_ui()
        scene.status_label.text = f"Undo: {label}"

    def redo(self) -> None:
        scene = self.scene
        if not scene.commands.can_redo:
            scene.status_label.text = "Nothing to redo"
            return
        label = scene.commands.redo_label or "command"
        result = scene.commands.redo()
        scene.document.mark_dirty()
        if result is not None:
            scene.selection.select(result)
        else:
            selected = scene.selection.selected
            if (
                selected is not None
                and not scene.document.scene.world.is_alive(selected.entity)
            ):
                scene.selection.clear()
        scene._sync_all_prefab_instance_overrides()
        scene._refresh_document_ui()
        scene.status_label.text = f"Redo: {label}"

    def sync_add_node_dialog_layout(self) -> None:
        scene = self.scene
        if not hasattr(scene, "add_node_dialog"):
            return

        content_w, content_h = scene.add_node_dialog.content.size
        scene.add_node_parent_label.position = (0.0, 0.0)

        list_top = 38.0
        reserved_bottom = 92.0
        list_height = max(120.0, content_h - list_top - reserved_bottom)

        scene.add_node_type_list.anchor = (0.5, 0.0)
        scene.add_node_type_list.pivot = (0.5, 0.5)
        scene.add_node_type_list.size = (max(100.0, content_w), list_height)
        scene.add_node_type_list.position = (0.0, list_top + list_height / 2.0)

        scene.add_node_name.anchor = (0.5, 1.0)
        scene.add_node_name.pivot = (0.5, 0.5)
        scene.add_node_name.size = (max(100.0, content_w), 42.0)
        scene.add_node_name.position = (0.0, -46.0)

    def sync_layout(self, width: float, height: float) -> None:
        scene = self.scene
        scene.scene_title.position = (12.0, 10.0)

        button_y = 52.0
        margin = 8.0
        gap = 6.0
        add_w = 34.0
        rename_w = 74.0
        delete_w = 74.0
        total_w = add_w + rename_w + delete_w + gap * 2.0
        start_x = max(margin, (width - total_w) * 0.5)

        scene.add_node_button.size = (add_w, 28.0)
        scene.add_node_button.anchor = (0.0, 0.0)
        scene.add_node_button.pivot = (0.5, 0.5)
        scene.add_node_button.position = (start_x + add_w / 2.0, button_y)

        rename_x = start_x + add_w + gap
        scene.rename_node_button.size = (rename_w, 28.0)
        scene.rename_node_button.anchor = (0.0, 0.0)
        scene.rename_node_button.pivot = (0.5, 0.5)
        scene.rename_node_button.position = (rename_x + rename_w / 2.0, button_y)

        delete_x = rename_x + rename_w + gap
        scene.delete_node_button.size = (delete_w, 28.0)
        scene.delete_node_button.anchor = (0.0, 0.0)
        scene.delete_node_button.pivot = (0.5, 0.5)
        scene.delete_node_button.position = (delete_x + delete_w / 2.0, button_y)

        list_top = 76.0
        scene.scene_list.anchor = (0.5, 0.0)
        scene.scene_list.pivot = (0.5, 0.5)
        scene.scene_list.size = (
            max(0.0, width - 16.0),
            max(0.0, height - list_top - 8.0),
        )
        scene.scene_list.position = (
            0.0,
            list_top + scene.scene_list.size[1] / 2.0,
        )


__all__ = ["SceneTreeController"]
