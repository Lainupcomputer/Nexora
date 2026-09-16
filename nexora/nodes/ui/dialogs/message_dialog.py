from __future__ import annotations

from nexora.nodes.ui.dialogs.confirm_dialog import ConfirmDialog


class MessageDialog(ConfirmDialog):
    """Informational dialog with one acknowledgement button."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.title = "Message"
        self.confirm_text = "OK"
        self.show_cancel_button = False
