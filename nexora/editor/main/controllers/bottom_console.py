from __future__ import annotations

from nexora.nodes import Label


class BottomConsolePanel:
    """Owns the Console tab UI, output refresh and layout."""

    def __init__(self, editor) -> None:
        self.editor = editor

    def build(self) -> None:
        e = self.editor
        e.console_content = e.bottom_dock.create_child(
            "ConsoleContent",
            node_type=Label,
        )
        e.console_content.text = "Console ready."
        e.console_content.scale = 0.66
        e.console_content.anchor = (0.0, 0.0)
        e.console_content.pivot = (0.0, 0.0)

        e.console_clear_button = e._button(
            e.bottom_dock,
            "ConsoleClearButton",
            "Clear",
            e._clear_editor_console,
        )

    def update(self) -> None:
        self.refresh_output()

    def set_visible(self, visible: bool) -> None:
        e = self.editor
        e.console_content.visible = visible
        e.console_clear_button.visible = visible

    def refresh_output(self) -> None:
        e = self.editor
        engine = getattr(e.game, "engine", None)
        console = getattr(engine, "console", None)
        if console is None:
            text = "No engine console available."
        else:
            lines = getattr(console, "lines", ())
            recent = tuple(lines)[-8:]
            text = "\n".join(
                getattr(line, "display_text", str(line))
                for line in recent
            ) or "Console ready."

        if e.console_content.text != text:
            e.console_content.text = text

    def clear(self) -> None:
        e = self.editor
        engine = getattr(e.game, "engine", None)
        console = getattr(engine, "console", None)
        if console is not None:
            console.clear()
        self.refresh_output()
        e.status_label.text = "Console cleared"

    def sync_layout(self, width: float, _height: float) -> None:
        e = self.editor
        toolbar_y = 49.0
        e.console_content.position = (18.0, 76.0)
        e.console_clear_button.size = (78.0, 28.0)
        e.console_clear_button.anchor = (1.0, 0.0)
        e.console_clear_button.pivot = (0.5, 0.5)
        e.console_clear_button.position = (width - 48.0, toolbar_y)
