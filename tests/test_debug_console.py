from __future__ import annotations

from types import SimpleNamespace

from nexora.debug.console import DebugConsole
from nexora.debug.console.autocomplete import AutocompleteEngine
from nexora.debug.console.history import CommandHistory
from nexora.debug.console.parser import parse_command
from nexora.debug.console.registry import CommandRegistry


def test_parser_supports_quoted_arguments():
    parsed = parse_command('spawn "enemy guard" 3')

    assert parsed is not None
    assert parsed.name == "spawn"
    assert parsed.args == ("enemy guard", "3")


def test_history_moves_back_and_forward():
    history = CommandHistory()
    history.add("help")
    history.add("fps")

    assert history.previous("") == "fps"
    assert history.previous("fps") == "help"
    assert history.next("help") == "fps"
    assert history.next("fps") == ""


def test_registry_resolves_aliases():
    registry = CommandRegistry()
    handler = lambda context: None

    command = registry.register(
        "quit",
        handler,
        aliases=("exit",),
    )

    assert registry.get("quit") is command
    assert registry.get("exit") is command


def test_autocomplete_completes_unique_command():
    registry = CommandRegistry()
    registry.register("timescale", lambda context: None)
    autocomplete = AutocompleteEngine(registry)

    result = autocomplete.complete("tim")

    assert result.text == "timescale "
    assert result.matches == ("timescale",)


def test_autocomplete_cycles_multiple_matches():
    registry = CommandRegistry()
    registry.register("scene", lambda context: None)
    registry.register("set", lambda context: None)
    autocomplete = AutocompleteEngine(registry)

    first = autocomplete.complete("s")
    second = autocomplete.complete("s")

    assert first.text != second.text
    assert set(first.matches) == {"scene", "set"}


class FakeInput:
    def __init__(self):
        self.capture = False
        self.allowed = set()
        self.started = False
        self.stopped = False
        self.text_input = ()

    def set_action_capture(self, active, *, allowed_actions=()):
        self.capture = bool(active)
        self.allowed = set(allowed_actions)

    def start_text_input(self):
        self.started = True

    def stop_text_input(self):
        self.stopped = True

    def key_pressed(self, key):
        return False


class FakeEngine:
    def __init__(self):
        self.input = FakeInput()
        self.loop = SimpleNamespace(target_fps=60)
        self.time = SimpleNamespace(time_scale=1.0)
        self.debug_overlay = SimpleNamespace(
            metrics=SimpleNamespace(
                snapshot=SimpleNamespace(fps=60.0)
            )
        )
        self.game = SimpleNamespace(scene=None)
        self.stopped = False

    def stop(self):
        self.stopped = True


def test_console_open_uses_action_capture_and_text_input():
    engine = FakeEngine()
    console = DebugConsole(engine)

    console.open()

    assert console.is_open
    assert engine.input.capture
    assert engine.input.allowed == {"debug_console"}
    assert engine.input.started

    console.close()

    assert not console.is_open
    assert not engine.input.capture
    assert engine.input.stopped


def test_console_executes_registered_command():
    engine = FakeEngine()
    console = DebugConsole(engine)
    calls = []

    def echo(context):
        calls.append(context.args)
        return "ok"

    console.register_command("echo", echo)

    assert console.execute("echo one two")
    assert calls == [("one", "two")]
    assert console.lines[-1].text == "ok"


def test_builtin_timescale_changes_engine_time():
    engine = FakeEngine()
    console = DebugConsole(engine)

    assert console.execute("timescale 0.5")
    assert engine.time.time_scale == 0.5
