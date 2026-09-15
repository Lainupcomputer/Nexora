from __future__ import annotations

from types import SimpleNamespace

from nexora.debug.console import DebugConsole
from nexora.debug.logger import Logger


class FakeInput:
    def __init__(self):
        self.text_input = ()

    def set_action_capture(self, active, *, allowed_actions=()):
        pass

    def acquire_text_input(self, owner):
        pass

    def release_text_input(self, owner):
        pass

    def key_pressed(self, key):
        return False

    def start_text_input(self):
        pass

    def stop_text_input(self):
        pass


class FakeNotifications:
    def __init__(self):
        self.errors = []

    def error(self, text, *, title=None, duration=3.0):
        self.errors.append((text, title, duration))
        return len(self.errors)


class FakeEngine:
    def __init__(self):
        self.logger = Logger("Nexora.Test.ConsoleBridge")
        self.input = FakeInput()
        self.loop = SimpleNamespace(target_fps=60)
        self.time = SimpleNamespace(time_scale=1.0)
        self.debug_overlay = SimpleNamespace(
            metrics=SimpleNamespace(
                snapshot=SimpleNamespace(fps=60.0)
            )
        )
        self.game = SimpleNamespace(
            scene=None,
            _notifications=FakeNotifications(),
        )

    def stop(self):
        pass


def test_logger_messages_are_mirrored_to_console():
    engine = FakeEngine()
    console = DebugConsole(engine)

    engine.logger.info("hello")
    engine.logger.warning("careful")

    assert console.lines[-2].display_text == "[INFO] hello"
    assert console.lines[-1].display_text == "[WARN] careful"

    console.shutdown()


def test_error_log_creates_notification():
    engine = FakeEngine()
    console = DebugConsole(engine)

    engine.logger.error("something broke")

    assert console.lines[-1].display_text == "[ERROR] something broke"
    assert engine.game._notifications.errors == [
        ("something broke", "Engine Error", 6.0)
    ]

    console.shutdown()


def test_critical_log_creates_critical_notification():
    engine = FakeEngine()
    console = DebugConsole(engine)

    engine.logger.critical("fatal")

    assert console.lines[-1].display_text == "[ERROR] fatal"
    assert engine.game._notifications.errors == [
        ("fatal", "Critical Error", 6.0)
    ]

    console.shutdown()


def test_shutdown_detaches_logger_bridge():
    engine = FakeEngine()
    console = DebugConsole(engine)
    console.shutdown()

    before = console.lines
    engine.logger.info("after shutdown")

    assert console.lines == before
