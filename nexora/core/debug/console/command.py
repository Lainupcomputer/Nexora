from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


CommandHandler = Callable[["CommandContext"], object]
CommandCompleter = Callable[[Sequence[str], str], Iterable[str]]


@dataclass(slots=True)
class CommandContext:
    console: object
    engine: object
    command: str
    args: tuple[str, ...]
    raw: str

    def write(self, message: object) -> None:
        self.console.write(str(message))

    def info(self, message: object) -> None:
        self.console.info(str(message))

    def warning(self, message: object) -> None:
        self.console.warning(str(message))

    def error(self, message: object) -> None:
        self.console.error(str(message))


@dataclass(slots=True)
class ConsoleCommand:
    name: str
    handler: CommandHandler
    description: str = ""
    usage: str = ""
    aliases: tuple[str, ...] = ()
    completer: CommandCompleter | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip().lower()
        self.aliases = tuple(
            alias.strip().lower()
            for alias in self.aliases
            if alias.strip()
        )

        if not self.name:
            raise ValueError("command name cannot be empty")
