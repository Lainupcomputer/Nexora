from __future__ import annotations

from dataclasses import dataclass

from nexora.debug.console.parser import completion_context
from nexora.debug.console.registry import CommandRegistry


@dataclass(slots=True)
class CompletionResult:
    text: str
    matches: tuple[str, ...] = ()


class AutocompleteEngine:
    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry
        self._matches: tuple[str, ...] = ()
        self._index = -1
        self._base = ""
        self._last_text: str | None = None
        self._source_text: str | None = None

    def reset(self) -> None:
        self._matches = ()
        self._index = -1
        self._base = ""
        self._last_text = None
        self._source_text = None

    def complete(self, text: str) -> CompletionResult:
        # Repeated Tab after a multi-match completion cycles through the
        # existing candidate set even though the visible input text has
        # already changed to the previous candidate.
        if (
            self._last_text is not None
            and (
                text == self._last_text
                or text == self._source_text
            )
            and len(self._matches) > 1
        ):
            self._index = (self._index + 1) % len(self._matches)
            completed_text = self._base + self._matches[self._index]
            self._last_text = completed_text
            return CompletionResult(completed_text, self._matches)

        completed, prefix, command_position = completion_context(text)

        if command_position:
            matches = self.registry.matches(prefix)
        else:
            command = self.registry.get(completed[0]) if completed else None

            if command is None or command.completer is None:
                self.reset()
                return CompletionResult(text=text)

            args = completed[1:]
            matches = tuple(
                sorted(
                    set(command.completer(args, prefix))
                )
            )

        if not matches:
            self.reset()
            return CompletionResult(text=text)

        base = text[: len(text) - len(prefix)] if prefix else text

        if len(matches) == 1:
            self.reset()
            return CompletionResult(
                text=base + matches[0] + " ",
                matches=matches,
            )

        self._matches = matches
        self._index = 0
        self._base = base
        self._source_text = text
        self._last_text = base + matches[0]

        return CompletionResult(
            text=self._last_text,
            matches=matches,
        )
