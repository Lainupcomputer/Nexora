from __future__ import annotations

from pathlib import Path

from nexora.core.game import Game
from nexora.nodes import Button, ConfirmDialog, FileDialog, Label
from nexora.scene import Scene


class DialogExample(Game):
    def __init__(self) -> None:
        super().__init__(
            title="Nexora Dialog UI",
            width=1100,
            height=700,
            resizable=True,
        )

        scene = Scene("DialogExample")
        self.scene = scene

        title = scene.ui.create_child("Title", node_type=Label)
        title.text = "Nexora Dialog V1"
        title.position = (0.0, -130.0)
        title.anchor = (0.5, 0.5)
        title.pivot = (0.5, 0.5)

        confirm_button = scene.ui.create_child("ConfirmButton", node_type=Button)
        confirm_button.text = "Open ConfirmDialog"
        confirm_button.size = (250.0, 52.0)
        confirm_button.position = (0.0, -45.0)

        file_button = scene.ui.create_child("FileButton", node_type=Button)
        file_button.text = "Open FileDialog"
        file_button.size = (250.0, 52.0)
        file_button.position = (0.0, 30.0)

        self.confirm_dialog = scene.ui.create_child("ConfirmDialog", node_type=ConfirmDialog)
        self.confirm_dialog.title = "Delete Node"
        self.confirm_dialog.message = "Do you really want to delete this node?"
        self.confirm_dialog.confirm_text = "Delete"
        self.confirm_dialog.confirmed.connect(
            lambda *_: print("[Dialog] confirmed")
        )

        self.file_dialog = scene.ui.create_child("FileDialog", node_type=FileDialog)
        self.file_dialog.configure(
            mode="open",
            root_path=Path.cwd(),
            extensions=(".nxscene", ".nxprefab"),
            title="Open Nexora Resource",
        )
        self.file_dialog.file_selected.connect(
            lambda _dialog, path: print(f"[Dialog] selected: {path}")
        )

        confirm_button.on_click = self.confirm_dialog.open
        file_button.on_click = self.file_dialog.open


if __name__ == "__main__":
    DialogExample().run()
