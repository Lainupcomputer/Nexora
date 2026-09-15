from __future__ import annotations

from collections.abc import Iterable

from nexora.debug.console.command import (
    CommandCompleter,
    CommandHandler,
    ConsoleCommand,
)


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, ConsoleCommand] = {}
        self._aliases: dict[str, str] = {}

    def register(
        self,
        name: str,
        handler: CommandHandler,
        *,
        description: str = "",
        usage: str = "",
        aliases: Iterable[str] = (),
        completer: CommandCompleter | None = None,
        replace: bool = False,
    ) -> ConsoleCommand:
        command = ConsoleCommand(
            name=name,
            handler=handler,
            description=description,
            usage=usage,
            aliases=tuple(aliases),
            completer=completer,
        )

        if not replace and command.name in self._commands:
            raise ValueError(
                f"Console command already registered: {command.name}"
            )

        if replace:
            self.unregister(command.name)

        for alias in command.aliases:
            if alias in self._commands:
                raise ValueError(
                    f"Console alias conflicts with command: {alias}"
                )

            current = self._aliases.get(alias)
            if current is not None and current != command.name:
                raise ValueError(
                    f"Console alias already registered: {alias}"
                )

        self._commands[command.name] = command

        for alias in command.aliases:
            self._aliases[alias] = command.name

        return command

    def unregister(self, name: str) -> bool:
        key = str(name).strip().lower()
        canonical = self._aliases.get(key, key)
        command = self._commands.pop(canonical, None)

        if command is None:
            return False

        for alias in command.aliases:
            self._aliases.pop(alias, None)

        return True

    def get(self, name: str) -> ConsoleCommand | None:
        key = str(name).strip().lower()
        canonical = self._aliases.get(key, key)
        return self._commands.get(canonical)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._commands))

    def commands(self) -> tuple[ConsoleCommand, ...]:
        return tuple(
            self._commands[name]
            for name in sorted(self._commands)
        )

    def matches(self, prefix: str) -> tuple[str, ...]:
        prefix = str(prefix).strip().lower()
        names = set(self._commands)
        names.update(self._aliases)
        return tuple(sorted(name for name in names if name.startswith(prefix)))
