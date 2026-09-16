from __future__ import annotations

from nexora.nodes.ui.dialogs.dialog import Dialog
from nexora.nodes.ui.output.label import Label


class ConfirmDialog(Dialog):
    """Small yes/no style dialog with a message body."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.title = "Confirm"
        self.confirm_text = "OK"
        self.cancel_text = "Cancel"
        self.dialog_size = (500.0, 240.0)
        self.message: str = ""

        self.message_label = self.content.create_child("Message", node_type=Label)
        self.message_label.anchor = (0.0, 0.0)
        self.message_label.pivot = (0.0, 0.0)
        self.message_label.position = (0.0, 0.0)
        self.message_label.scale = 0.95

    def _sync_layout(self) -> None:
        super()._sync_layout()
        self.message_label.text = self.message
