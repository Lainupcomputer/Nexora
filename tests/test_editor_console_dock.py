from types import SimpleNamespace

from nexora.debug.console import ConsoleLevel, ConsoleLine
from nexora.editor.scene import EditorScene


def test_editor_console_output_uses_recent_engine_lines() -> None:
    scene = EditorScene.__new__(EditorScene)
    scene.game = SimpleNamespace(
        engine=SimpleNamespace(
            console=SimpleNamespace(
                lines=(
                    ConsoleLine("old", ConsoleLevel.INFO),
                    ConsoleLine("latest", ConsoleLevel.ERROR),
                ),
            ),
        ),
    )
    scene.console_content = SimpleNamespace(text="")

    scene._refresh_console_output()

    assert scene.console_content.text == "[INFO] old\n[ERROR] latest"


def test_editor_console_clear_clears_engine_console() -> None:
    console = SimpleNamespace(
        lines=(ConsoleLine("message"),),
        clear_calls=0,
    )

    def clear() -> None:
        console.clear_calls += 1
        console.lines = ()

    console.clear = clear
    scene = EditorScene.__new__(EditorScene)
    scene.game = SimpleNamespace(engine=SimpleNamespace(console=console))
    scene.console_content = SimpleNamespace(text="message")
    scene.status_label = SimpleNamespace(text="")

    scene._clear_editor_console()

    assert console.clear_calls == 1
    assert scene.console_content.text == "Console ready."
    assert scene.status_label.text == "Console cleared"
