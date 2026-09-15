from __future__ import annotations

from nexora.debug.logger import LogEvent, LogLevel


class ConsoleLogBridge:
    """Mirror engine logger events into the global debug console.

    Error notifications are emitted by ``DebugConsole.error()`` itself so
    direct console errors and logger errors share exactly the same behavior.
    """

    def __init__(self, console, engine) -> None:
        self.console = console
        self.engine = engine
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return

        logger = getattr(self.engine, "logger", None)
        add_listener = getattr(logger, "add_listener", None)

        if add_listener is None:
            return

        add_listener(self.handle)
        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return

        logger = getattr(self.engine, "logger", None)
        remove_listener = getattr(logger, "remove_listener", None)

        if remove_listener is not None:
            remove_listener(self.handle)

        self._attached = False

    def handle(self, event: LogEvent) -> None:
        if event.level is LogLevel.DEBUG:
            self.console.debug(event.message)
        elif event.level is LogLevel.INFO:
            self.console.info(event.message)
        elif event.level is LogLevel.WARNING:
            self.console.warning(event.message)
        elif event.level is LogLevel.CRITICAL:
            self.console.error(
                event.message,
                title="Critical Error",
                duration=6.0,
            )
        else:
            self.console.error(
                event.message,
                title="Engine Error",
                duration=6.0,
            )
