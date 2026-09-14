from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SaveOperation(
    str,
    Enum,
):
    """
    Operation performed by the save system.
    """

    SAVE = "save"
    LOAD = "load"
    DELETE = "delete"


class SaveKind(
    str,
    Enum,
):
    """
    Type of save slot involved in an operation.
    """

    MANUAL = "manual"
    QUICK = "quick"
    AUTO = "auto"


class SaveEventState(
    str,
    Enum,
):
    """
    Lifecycle state of a save operation.
    """

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(
    slots=True,
    frozen=True,
)
class SaveEvent:
    """
    Event emitted by SaveManager.

    SaveManager itself has no dependency on UI or notification
    systems. Consumers can subscribe to these events and decide
    how they should be presented.

    Examples
    --------

        SAVE / MANUAL / STARTED
        SAVE / QUICK  / COMPLETED
        SAVE / AUTO   / FAILED
        LOAD / MANUAL / COMPLETED
    """

    operation: SaveOperation
    kind: SaveKind
    state: SaveEventState
    slot: str

    metadata: Any | None = None
    error: BaseException | None = None