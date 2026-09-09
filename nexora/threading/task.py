from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, Enum
from typing import Any, Callable

from nexora.threading.future import Future


class TaskPriority(IntEnum):
    """
    Priority of a scheduled task.

    Higher values are executed first.
    """

    LOW = 10
    NORMAL = 20
    HIGH = 30


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Task:
    id: int
    function: Callable[..., Any]
    args: tuple
    kwargs: dict
    future: Future
    priority: TaskPriority = TaskPriority.NORMAL

    status: TaskStatus = TaskStatus.PENDING
    created_at: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0

    def execution_time(self) -> float:
        if self.started_at <= 0:
            return 0.0

        end = self.finished_at

        if end <= 0:
            return 0.0

        return end - self.started_at