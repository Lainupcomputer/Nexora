from __future__ import annotations

import shlex
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    name: str
    args: tuple[str, ...]
    raw: str


def parse_command(text: str) -> ParsedCommand | None:
    raw = str(text).strip()

    if not raw:
        return None

    parts = shlex.split(raw, posix=True)

    if not parts:
        return None

    return ParsedCommand(
        name=parts[0].lower(),
        args=tuple(parts[1:]),
        raw=raw,
    )


def completion_context(text: str) -> tuple[tuple[str, ...], str, bool]:
    """
    Return (completed_tokens, current_prefix, command_position).

    This parser is intentionally tolerant of unfinished quotes because
    autocomplete must continue working while the user is still typing.
    """

    raw = str(text)
    ends_with_space = bool(raw) and raw[-1].isspace()

    try:
        tokens = shlex.split(raw, posix=True)
    except ValueError:
        # Fallback for incomplete quotes.
        tokens = raw.split()

    if ends_with_space:
        completed = tuple(tokens)
        prefix = ""
    elif tokens:
        completed = tuple(tokens[:-1])
        prefix = tokens[-1]
    else:
        completed = ()
        prefix = raw.strip()

    return completed, prefix, len(completed) == 0
