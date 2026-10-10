from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexora.editor.main.scene import EditorScene


class DocumentController:
    """Own scene-document file workflow for the main Nexora editor."""

    def __init__(self, editor: "EditorScene") -> None:
        self.editor = editor
        self._pending_action: Callable[[], None] | None = None
        self._prefab_save_node = None

    def run_after_dirty_check(self, action: Callable[[], None]) -> None:
        if self.editor.document.dirty:
            self._pending_action = action
            self.editor.unsaved_dialog.open()
            return
        action()

    def continue_pending_action(self) -> None:
        action = self._pending_action
        self._pending_action = None
        if action is not None:
            action()

    def clear_pending_action(self) -> None:
        self._pending_action = None

    def request_new_scene(self) -> None:
        self.run_after_dirty_check(self.open_new_scene_dialog)

    def open_new_scene_dialog(self) -> None:
        self.editor.new_scene_name.set_text("Untitled", emit=False)
        self.editor.new_scene_dialog.open(focus=self.editor.new_scene_name)

    def create_scene_from_dialog(self) -> None:
        name = self.editor.new_scene_name.text.strip() or "Untitled"
        self.editor.document.new(name)
        self.editor.commands.clear()
        self.editor.selection.clear()
        self.editor._refresh_document_ui()
        self.editor.status_label.text = f"Created scene {name}"

    def request_open_scene(self) -> None:
        self.run_after_dirty_check(self.open_scene_file_dialog)

    def scene_start_directory(self) -> Path:
        scenes = self.editor.project_context.scenes_root
        if scenes.is_dir():
            return scenes
        return self.editor.project_path

    def open_scene_file_dialog(self) -> None:
        self.editor.open_scene_dialog.configure(
            mode="open",
            root_path=self.editor.project_path,
            current_path=self.scene_start_directory(),
            extensions=(".nxscene",),
            title="Open Scene",
        )
        self.editor.open_scene_dialog.open()

    def on_open_scene_selected(self, _dialog, path: Path) -> None:
        try:
            self.editor.document.load(
                self.editor.game.scene_serializer,
                path,
                context=self.editor._serialization_context(),
            )
        except Exception as exc:
            self.editor._show_error(f"Could not open scene:\n{exc}")
            return

        self.editor.commands.clear()
        self.editor.selection.clear()
        self.editor._refresh_document_ui()
        self.editor.status_label.text = f"Opened {path.name}"

    def save_scene(self) -> None:
        if self.editor.document.path is None:
            self.save_scene_as()
            return

        self.editor._sync_all_prefab_instance_overrides()

        try:
            path = self.editor.document.save(self.editor.game.scene_serializer)
        except Exception as exc:
            self.editor._show_error(f"Could not save scene:\n{exc}")
            return

        self.editor._refresh_document_ui()
        self.editor.status_label.text = f"Saved {path.name}"

    def save_selected_prefab(self) -> None:
        node = self.editor._editable_selected_node()
        if node is None:
            self.editor.status_label.text = (
                "Select a node to save as a prefab first"
            )
            return

        start = self.editor.project_context.prefabs_root
        if not start.is_dir():
            start = self.editor.project_context.assets_root
        if not start.is_dir():
            start = self.editor.project_path

        self._prefab_save_node = node
        self.editor.save_prefab_dialog.configure(
            mode="save",
            root_path=self.editor.project_path,
            current_path=start,
            extensions=(".nxprefab",),
            title="Save Prefab As",
        )
        self.editor.save_prefab_dialog.filename_input.set_text(
            f"{node.name}.nxprefab",
            emit=False,
        )
        self.editor.save_prefab_dialog.open(
            focus=self.editor.save_prefab_dialog.filename_input
        )

    def on_save_prefab_selected(self, _dialog, path: Path) -> None:
        node = self._prefab_save_node
        self._prefab_save_node = None

        if node is None:
            return

        try:
            saved = self.editor.game.scene_serializer.prefabs.save(node, path)
        except Exception as exc:
            self.editor._show_error(f"Could not save prefab:\n{exc}")
            return

        self.editor._refresh_asset_browser(preserve_selection=False)
        self.editor.status_label.text = f"Saved prefab {saved.name}"

    def save_scene_as(self) -> None:
        self.editor.save_scene_dialog.configure(
            mode="save",
            root_path=self.editor.project_path,
            current_path=self.scene_start_directory(),
            extensions=(".nxscene",),
            title="Save Scene As",
        )
        self.editor.save_scene_dialog.filename_input.set_text(
            f"{self.editor.document.display_name}.nxscene",
            emit=False,
        )
        self.editor.save_scene_dialog.open(
            focus=self.editor.save_scene_dialog.filename_input
        )

    def on_save_scene_selected(self, _dialog, path: Path) -> None:
        self.editor._sync_all_prefab_instance_overrides()

        try:
            saved = self.editor.document.save_as(
                self.editor.game.scene_serializer,
                path,
            )
        except Exception as exc:
            self.editor._show_error(f"Could not save scene:\n{exc}")
            return

        self.editor._refresh_document_ui()
        self.editor.status_label.text = f"Saved {saved.name}"
