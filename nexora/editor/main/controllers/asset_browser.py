from __future__ import annotations

from pathlib import Path

from nexora.editor.commands import (
    AddImageSpriteCommand,
    InstantiatePrefabCommand,
    TileMapAssetCommand,
)
from nexora.editor.main.asset_browser import (
    AssetBrowserModel,
    format_file_size,
    reveal_in_file_manager,
)
from nexora.nodes import Label, Panel
from nexora.nodes.world.tilemap_node import TileMapNode


class AssetBrowserController:
    """Asset browser interaction, activation and viewport drag/drop workflow."""

    DRAG_THRESHOLD = 7.0

    def __init__(self, scene) -> None:
        self.scene = scene
        self.ensure_state()

    def ensure_state(self) -> None:
        scene = self.scene
        if not hasattr(scene, "asset_browser"):
            scene.asset_browser = AssetBrowserModel(scene.project_path)
        if not hasattr(scene, "_asset_entries"):
            scene._asset_entries = []
        if not hasattr(scene, "_selected_asset"):
            scene._selected_asset = None
        if not hasattr(scene, "_asset_drag_payload"):
            scene._asset_drag_payload = None
        if not hasattr(scene, "_asset_pointer_press"):
            scene._asset_pointer_press = None
        if not hasattr(scene, "_asset_drag_active"):
            scene._asset_drag_active = False
        if not hasattr(scene, "_asset_drag_entry"):
            scene._asset_drag_entry = None
        if not hasattr(scene, "_asset_drag_threshold"):
            scene._asset_drag_threshold = self.DRAG_THRESHOLD

    def build_drag_overlay(self) -> None:
        scene = self.scene
        scene.asset_drag_badge = scene.ui.create_child(
            "AssetDragBadge",
            node_type=Panel,
        )
        scene.asset_drag_badge.size = (220.0, 34.0)
        scene.asset_drag_badge.anchor = (0.5, 0.5)
        scene.asset_drag_badge.pivot = (0.5, 0.5)
        scene.asset_drag_badge.background = (30, 33, 38, 245)
        scene.asset_drag_badge.border_color = (80, 120, 190, 255)
        scene.asset_drag_badge.border_width = 1.0
        scene.asset_drag_badge.border_radius = 5.0
        scene.asset_drag_badge.visible = False

        scene.asset_drag_label = scene.asset_drag_badge.create_child(
            "AssetDragLabel",
            node_type=Label,
        )
        scene.asset_drag_label.anchor = (0.5, 0.5)
        scene.asset_drag_label.pivot = (0.5, 0.5)
        scene.asset_drag_label.scale = 0.58

    def refresh(self, preserve_selection: bool = True) -> None:
        scene = self.scene
        self.ensure_state()
        if not hasattr(scene, "asset_list"):
            return

        selected_path = (
            scene._selected_asset.path
            if preserve_selection and scene._selected_asset is not None
            else None
        )
        scene._asset_entries = scene.asset_browser.refresh()
        scene.asset_list.set_items(
            [entry.display_name for entry in scene._asset_entries]
        )
        scene.asset_path_label.text = (
            f"Project / {scene.asset_browser.relative_directory}"
        )
        scene.asset_up_button.enabled = scene.asset_browser.can_go_up

        restored = False
        if selected_path is not None:
            for index, entry in enumerate(scene._asset_entries):
                if entry.path == selected_path:
                    scene.asset_list.set_selected_index(index, emit=False)
                    self.set_selected(entry)
                    restored = True
                    break

        if not restored:
            scene.asset_list.selected_index = -1
            self.set_selected(None)

        if hasattr(scene, "status_label"):
            scene.status_label.text = f"Assets: {len(scene._asset_entries)} item(s)"

    def on_search_changed(self, text: str) -> None:
        scene = self.scene
        scene.asset_browser.set_search(text)
        self.refresh(preserve_selection=False)

    def go_up(self) -> None:
        scene = self.scene
        scene.asset_browser.go_up()
        scene.asset_search.set_text("", emit=False)
        scene.asset_browser.search_text = ""
        self.refresh(preserve_selection=False)

    def set_selected(self, entry) -> None:
        scene = self.scene
        scene._selected_asset = entry
        scene._asset_drag_payload = None if entry is None else entry.drag_payload

        if entry is None:
            scene.asset_preview.set_asset(None)
            scene.asset_details.text = (
                "Select an asset.\n"
                "Double-click folders/scenes to open."
            )
            return

        scene.asset_preview.set_asset(entry.path if entry.kind == "image" else None)
        size_text = "Folder" if entry.is_directory else format_file_size(entry.size_bytes)
        scene.asset_details.text = (
            f"{entry.name}\n"
            f"Type: {entry.kind}\n"
            f"Size: {size_text}\n"
            f"{entry.relative_path}"
        )

    def on_selected(self, index: int, _label: str | None) -> None:
        scene = self.scene
        entry = scene.asset_browser.entry_at(index)
        self.set_selected(entry)
        if entry is not None:
            scene.status_label.text = f"Selected asset: {entry.relative_path}"

    def activate_scene(self, path: Path) -> None:
        scene = self.scene

        def do_open() -> None:
            scene.document_controller.on_open_scene_selected(
                scene.open_scene_dialog,
                path,
            )

        scene.document_controller.run_after_dirty_check(do_open)

    def on_activated(self, index: int, _label: str) -> None:
        scene = self.scene
        entry = scene.asset_browser.entry_at(index)
        if entry is None:
            return

        if entry.is_directory:
            try:
                scene.asset_browser.navigate(entry.path)
            except Exception as exc:
                scene._show_error(f"Could not open folder:\n{exc}")
                return
            scene.asset_search.set_text("", emit=False)
            scene.asset_browser.search_text = ""
            self.refresh(preserve_selection=False)
            return

        if entry.kind == "scene":
            self.activate_scene(entry.path)
        elif entry.kind == "prefab":
            scene.status_label.text = (
                "Prefab selected. Drag it into the viewport to instantiate it."
            )
        elif entry.kind == "tilemap":
            self.assign_tilemap_asset(entry.path)
        elif entry.kind == "image":
            scene.status_label.text = f"Previewing {entry.name}"
        else:
            scene.status_label.text = f"Asset: {entry.relative_path}"

    def assign_tilemap_asset(self, path: Path) -> None:
        scene = self.scene
        node = scene.selection.selected
        if not isinstance(node, TileMapNode):
            scene.status_label.text = (
                "Select a TileMapNode before opening a TileMap asset."
            )
            return

        engine = scene.game.engine
        assets = getattr(engine, "assets", None)
        if assets is None:
            scene._show_error("The engine asset manager is not available.")
            return

        try:
            relative_path = path.resolve().relative_to(
                Path(assets.root).resolve()
            ).as_posix()
            scene.commands.execute(TileMapAssetCommand(node, relative_path, assets))
        except ValueError:
            scene._show_error(
                "The TileMap asset must be inside the project's assets folder."
            )
            return
        except Exception as exc:
            scene._show_error(f"Could not load TileMap asset:\n{exc}")
            return

        scene.document.mark_dirty()
        scene._refresh_inspector()
        scene._refresh_scene_tree()
        scene.status_label.text = f"Assigned TileMap: {relative_path}"

    def drop_image_in_viewport(self, entry, mouse_x: float, mouse_y: float) -> None:
        scene = self.scene
        if entry is None or entry.kind != "image" or scene.game.engine is None:
            return

        center_x, center_y = scene.viewport_canvas.calculate_position()
        world_x, world_y = scene.viewport_state.screen_to_world(
            mouse_x,
            mouse_y,
            center_x,
            center_y,
        )
        name = scene._unique_node_name(entry.path.stem)
        command = AddImageSpriteCommand(
            parent=scene.document.scene.root,
            registry=scene.game.scene_serializer.registry,
            assets=scene.game.engine.assets,
            asset_path=entry.path,
            name=name,
            x=world_x,
            y=world_y,
            context=scene._serialization_context(),
        )
        try:
            node = scene.commands.execute(command)
        except Exception as exc:
            scene._show_error(f"Could not create sprite from asset:\n{exc}")
            return

        scene.document.mark_dirty()
        scene.selection.select(node)
        scene._refresh_document_ui()
        scene.status_label.text = f"Created sprite '{name}' from {entry.name}"

    def drop_prefab_in_viewport(self, entry, mouse_x: float, mouse_y: float) -> None:
        scene = self.scene
        if entry is None or entry.kind != "prefab":
            return

        center_x, center_y = scene.viewport_canvas.calculate_position()
        world_x, world_y = scene.viewport_state.screen_to_world(
            mouse_x,
            mouse_y,
            center_x,
            center_y,
        )
        name = scene._unique_node_name(entry.path.stem)
        serializer = scene.game.scene_serializer
        command = InstantiatePrefabCommand(
            parent=scene.document.scene.root,
            prefab_serializer=serializer.prefabs,
            registry=serializer.registry,
            prefab_path=entry.path,
            name=name,
            x=world_x,
            y=world_y,
            context=scene._serialization_context(),
        )
        try:
            node = scene.commands.execute(command)
        except Exception as exc:
            scene._show_error(f"Could not instantiate prefab:\n{exc}")
            return

        scene.document.mark_dirty()
        scene.selection.select(node)
        scene._refresh_document_ui()
        scene.status_label.text = f"Instantiated prefab '{name}' from {entry.name}"

    def reset_drag(self) -> None:
        scene = self.scene
        scene._asset_pointer_press = None
        scene._asset_drag_active = False
        scene._asset_drag_entry = None
        if hasattr(scene, "asset_drag_badge"):
            scene.asset_drag_badge.visible = False

    def update_drag_input(self) -> None:
        scene = self.scene
        self.ensure_state()
        if scene._bottom_tab != "assets" or scene._any_editor_dialog_open():
            self.reset_drag()
            return

        input_manager = scene.game.input
        mouse_x, mouse_y = scene._viewport_mouse_centered()

        if scene._asset_pointer_press is None and input_manager.mouse_pressed("left"):
            hovered = scene.asset_list.hovered_index
            if 0 <= hovered < len(scene._asset_entries):
                entry = scene._asset_entries[hovered]
                if not entry.is_directory and entry.kind in {"image", "prefab"}:
                    scene._asset_pointer_press = (mouse_x, mouse_y)
                    scene._asset_drag_entry = entry

        if scene._asset_pointer_press is not None and input_manager.mouse_down("left"):
            start_x, start_y = scene._asset_pointer_press
            dx = mouse_x - start_x
            dy = mouse_y - start_y
            threshold = scene._asset_drag_threshold
            if not scene._asset_drag_active and dx * dx + dy * dy >= threshold * threshold:
                scene._asset_drag_active = True

            if scene._asset_drag_active:
                entry = scene._asset_drag_entry
                scene.asset_drag_badge.visible = True
                scene.asset_drag_badge.position = (mouse_x + 118.0, mouse_y + 24.0)
                target = "Image -> Sprite" if entry.kind == "image" else "Prefab -> Instance"
                scene.asset_drag_label.text = f"Drop {target}  |  {entry.name}"
                scene.asset_drag_badge.border_color = (
                    (70, 190, 110, 255)
                    if scene._mouse_inside_viewport_canvas()
                    else (80, 120, 190, 255)
                )

        if scene._asset_pointer_press is not None and input_manager.mouse_released("left"):
            entry = scene._asset_drag_entry
            should_drop = (
                scene._asset_drag_active and scene._mouse_inside_viewport_canvas()
            )
            self.reset_drag()
            if not should_drop:
                return
            if entry.kind == "image":
                self.drop_image_in_viewport(entry, mouse_x, mouse_y)
            elif entry.kind == "prefab":
                self.drop_prefab_in_viewport(entry, mouse_x, mouse_y)

    def context_open_selected(self) -> None:
        scene = self.scene
        entry = scene._selected_asset
        if entry is None:
            return
        try:
            index = scene._asset_entries.index(entry)
        except ValueError:
            return
        self.on_activated(index, entry.display_name)
        scene.asset_context.visible = False

    def context_reveal_selected(self) -> None:
        scene = self.scene
        entry = scene._selected_asset
        if entry is None:
            return
        try:
            reveal_in_file_manager(entry.path)
        except Exception as exc:
            scene._show_error(f"Could not reveal asset:\n{exc}")
        scene.asset_context.visible = False

    def update_context_input(self) -> None:
        scene = self.scene
        if scene._bottom_tab != "assets":
            scene.asset_context.visible = False
            return

        input_manager = scene.game.input
        if input_manager.mouse_pressed("right"):
            hovered = scene.asset_list.hovered_index
            if 0 <= hovered < len(scene._asset_entries):
                scene.asset_list.set_selected_index(hovered)
                self.set_selected(scene._asset_entries[hovered])
                scene.asset_context.visible = True
            else:
                scene.asset_context.visible = False
        elif (
            input_manager.mouse_pressed("left")
            and scene.asset_context.visible
            and scene.asset_list.hovered_index >= 0
        ):
            scene.asset_context.visible = False

    @property
    def drag_payload(self):
        self.ensure_state()
        return self.scene._asset_drag_payload
