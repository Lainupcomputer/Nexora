from __future__ import annotations

import itertools
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from nexora.debug.logger import Logger
from nexora.threading.future import Future
from nexora.threading.task import (
    Task,
    TaskPriority,
    TaskStatus,
)
from nexora.threading.worker import Worker


@dataclass(slots=True)
class SchedulerStats:
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    total_execution_time: float = 0.0

    @property
    def average_execution_time(self) -> float:
        if self.completed_tasks == 0:
            return 0.0

        return self.total_execution_time / self.completed_tasks


class TaskScheduler:
    """
    Nexora's CPU task scheduler.

    Uses real worker threads and a priority queue.

    Intended for Python 3.13 free-threading builds where CPU-bound
    Python code can execute concurrently.
    """

    def __init__(
        self,
        workers: int | None = None,
        *,
        logger: Logger | None = None,
    ):
        cpu_count = os.cpu_count() or 1

        if workers is None:
            workers = max(1, cpu_count - 1)

        if workers < 1:
            raise ValueError("Worker count must be at least 1.")

        self.worker_count = workers

        self._queue = queue.PriorityQueue()
        self._stop_event = threading.Event()

        # Worker pool
        self._workers: list[Worker] = []

        # Task registry
        self._tasks: dict[int, Task] = {}
        self._tasks_lock = threading.Lock()

        # Task IDs
        self._task_counter = itertools.count()

        # Scheduler state
        self._state_lock = threading.Lock()
        self._stats_lock = threading.Lock()

        self._started = False
        self._shutdown = False

        self._stats = SchedulerStats()

        self.logger = logger or Logger("Nexora.TaskScheduler")
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._state_lock:
            if self._started:
                return

            if self._shutdown:
                raise RuntimeError(
                    "TaskScheduler has already been shut down."
                )

            self._started = True

            for worker_id in range(self.worker_count):
                worker = Worker(
                    task_queue=self._queue,
                    worker_id=worker_id,
                    stop_event=self._stop_event,
                    on_task_finished=self._task_finished,
                    logger=self.logger,
                )

                self._workers.append(worker)
                worker.start()

    def shutdown(self, wait: bool = True) -> None:
        with self._state_lock:
            if self._shutdown:
                return

            self._shutdown = True

        # Allow currently queued work to finish.
        for _ in self._workers:
            self._queue.put(
                (
                    TaskPriority.LOW,
                    next(self._task_counter),
                    None,
                )
            )

        if wait:
            for worker in self._workers:
                worker.join()

            self._workers.clear()
            self._stop_event.set()

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit(
        self,
        function: Callable[..., Any],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs,
    ) -> Future:
        if not callable(function):
            raise TypeError("function must be callable.")

        if not isinstance(priority, TaskPriority):
            priority = TaskPriority(priority)

        with self._state_lock:
            if self._shutdown:
                raise RuntimeError("Cannot submit task after shutdown.")

        if not self._started:
            self.start()

        task_id = next(self._task_counter)

        future = Future()

        task = Task(
            id=task_id,
            function=function,
            args=args,
            kwargs=kwargs,
            future=future,
            priority=priority,
            created_at=time.perf_counter(),
        )

        # Task registrieren.
        with self._tasks_lock:
            self._tasks[task_id] = task

        # Statistik aktualisieren.
        with self._stats_lock:
            self._stats.total_tasks += 1

        # In Priority Queue einreihen.
        self._queue.put(
            (-int(priority), task_id, task)
        )

        return future
    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait_all(
        self,
        futures: Iterable[Future],
    ) -> list[Any]:
        return [
            future.result()
            for future in futures
        ]

    def wait_any(
        self,
        futures: Iterable[Future],
        timeout: float | None = None,
    ) -> Future | None:
        futures = list(futures)

        if not futures:
            return None

        condition = threading.Condition()
        completed: list[Future] = []
        completed_ids: set[int] = set()

        def callback(future: Future) -> None:
            identity = id(future)

            with condition:
                if identity in completed_ids:
                    return

                completed_ids.add(identity)
                completed.append(future)
                condition.notify()

        for future in futures:
            future.add_done_callback(callback)

        with condition:
            if not completed:
                condition.wait_for(
                    lambda: bool(completed),
                    timeout=timeout,
                )

            return completed[0] if completed else None

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel_all_pending(self) -> int:
        cancelled = 0

        while True:
            try:
                _, _, task = self._queue.get_nowait()
            except queue.Empty:
                break

            try:
                if task is None:
                    self._queue.put(
                        (
                            TaskPriority.LOW,
                            next(self._task_counter),
                            None,
                        )
                    )
                    continue

                if task.future.cancel():
                    task.status = TaskStatus.CANCELLED
                    cancelled += 1

            finally:
                self._queue.task_done()

            self._task_finished(task)

        return cancelled

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> SchedulerStats:
        with self._stats_lock:
            return SchedulerStats(
                total_tasks=self._stats.total_tasks,
                completed_tasks=self._stats.completed_tasks,
                failed_tasks=self._stats.failed_tasks,
                cancelled_tasks=self._stats.cancelled_tasks,
                total_execution_time=self._stats.total_execution_time,
            )

    def pending_tasks(self) -> int:
        return self._queue.qsize()

    def active_workers(self) -> int:
        return sum(
            worker.is_alive()
            for worker in self._workers
        )

    def active_tasks(self) -> int:
        return sum(
            worker.current_task is not None
            for worker in self._workers
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _task_finished(self, task: Task) -> None:
        with self._tasks_lock:
            self._tasks.pop(task.id, None)

        with self._stats_lock:
            if task.status is TaskStatus.COMPLETED:
                self._stats.completed_tasks += 1
                self._stats.total_execution_time += (
                    task.execution_time()
                )

            elif task.status is TaskStatus.FAILED:
                self._stats.failed_tasks += 1

            elif task.status is TaskStatus.CANCELLED:
                self._stats.cancelled_tasks += 1

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def started(self) -> bool:
        return self._started

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown