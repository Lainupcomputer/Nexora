from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class LogEvent:
    level: LogLevel
    message: str
    logger_name: str


LogListener = Callable[[LogEvent], None]


class Logger:
    def __init__(self, name="Nexora"):
        self._logger = logging.getLogger(name)
        self._listeners: list[LogListener] = []

        if not self._logger.handlers:
            handler = logging.StreamHandler()

            formatter = logging.Formatter(
                "[%(levelname)s] %(message)s"
            )

            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

        self._logger.setLevel(logging.INFO)

    @property
    def name(self) -> str:
        return self._logger.name

    def add_listener(self, listener: LogListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: LogListener) -> None:
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    def _emit(self, level: LogLevel, message: object) -> None:
        text = str(message)

        if level is LogLevel.DEBUG:
            self._logger.debug(text)
        elif level is LogLevel.INFO:
            self._logger.info(text)
        elif level is LogLevel.WARNING:
            self._logger.warning(text)
        elif level is LogLevel.ERROR:
            self._logger.error(text)
        else:
            self._logger.critical(text)

        if not self._listeners:
            return

        event = LogEvent(
            level=level,
            message=text,
            logger_name=self._logger.name,
        )

        for listener in tuple(self._listeners):
            try:
                listener(event)
            except Exception:
                # Logging must never fail because a debug sink broke.
                continue

    def debug(self, message):
        self._emit(LogLevel.DEBUG, message)

    def info(self, message):
        self._emit(LogLevel.INFO, message)

    def warning(self, message):
        self._emit(LogLevel.WARNING, message)

    def error(self, message):
        self._emit(LogLevel.ERROR, message)

    def critical(self, message):
        self._emit(LogLevel.CRITICAL, message)
