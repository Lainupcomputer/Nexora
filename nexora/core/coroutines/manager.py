from __future__ import annotations

import inspect
import threading

from .task import CoroutineTask


class TaskManager:
    """Global cooperative coroutine scheduler for Nexora."""

    def __init__(self) -> None:
        self._tasks: list[CoroutineTask] = []
        self._pending: list[CoroutineTask] = []
        self._updating = False
        self._paused = False
        self._lock = threading.RLock()

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(
                1
                for task in (
                    *self._tasks,
                    *self._pending,
                )
                if task.active
            )

    @property
    def tasks(self) -> tuple[CoroutineTask, ...]:
        with self._lock:
            return tuple(
                self._tasks
                + self._pending
            )

    def start(
        self,
        routine,
        *args,
        owner: object | None = None,
        ignore_time_scale: bool = False,
        name: str | None = None,
        **kwargs,
    ) -> CoroutineTask:
        if inspect.isgeneratorfunction(routine):
            routine = routine(
                *args,
                **kwargs,
            )
        else:
            if args or kwargs:
                raise TypeError(
                    "Arguments may only be supplied when starting "
                    "a generator function."
                )

        task = CoroutineTask(
            routine,
            owner=owner,
            ignore_time_scale=ignore_time_scale,
            name=name,
        )

        return self.add(task)

    run = start

    def add(
        self,
        task: CoroutineTask,
    ) -> CoroutineTask:
        if not isinstance(task, CoroutineTask):
            raise TypeError(
                "TaskManager.add() expects CoroutineTask."
            )

        with self._lock:
            if self._updating:
                self._pending.append(task)
            else:
                self._tasks.append(task)

        return task

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def clear(self) -> None:
        with self._lock:
            tasks = tuple(
                self._tasks
                + self._pending
            )
            self._tasks.clear()
            self._pending.clear()

        for task in tasks:
            task.cancel()

    def kill_owner(self, owner: object) -> int:
        killed = 0

        with self._lock:
            tasks = tuple(
                self._tasks
                + self._pending
            )

        for task in tasks:
            if task.owner is owner and task.active:
                task.cancel()
                killed += 1

        self._prune()
        return killed

    def update(
        self,
        scaled_delta: float,
        unscaled_delta: float | None = None,
    ) -> None:
        if self._paused:
            return

        if unscaled_delta is None:
            unscaled_delta = scaled_delta

        with self._lock:
            self._updating = True
            tasks = tuple(self._tasks)

        survivors: list[CoroutineTask] = []
        pending_error: BaseException | None = None

        try:
            for index, task in enumerate(tasks):
                try:
                    if task.update(
                        float(scaled_delta),
                        float(unscaled_delta),
                    ):
                        survivors.append(task)

                except BaseException as error:
                    # Preserve tasks that were not reached this frame.
                    # The failing task has already marked itself failed.
                    survivors.extend(
                        remaining
                        for remaining in tasks[index + 1 :]
                        if remaining.active
                    )
                    pending_error = error
                    break
        finally:
            with self._lock:
                self._tasks = survivors

                if self._pending:
                    self._tasks.extend(
                        self._pending
                    )
                    self._pending.clear()

                self._updating = False

        if pending_error is not None:
            raise pending_error

    def _prune(self) -> None:
        with self._lock:
            self._tasks = [
                task
                for task in self._tasks
                if task.active
            ]
            self._pending = [
                task
                for task in self._pending
                if task.active
            ]
