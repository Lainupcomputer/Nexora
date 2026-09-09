from __future__ import annotations

import queue
import threading
import time

from nexora.debug.logger import Logger
from nexora.threading.context import ThreadContext
from nexora.threading.task import Task, TaskStatus


class Worker:
    def __init__(
        self,
        task_queue,
        worker_id: int,
        stop_event: threading.Event,
        on_task_finished=None,
        logger: Logger | None = None,
    ):
        self.task_queue = task_queue
        self.worker_id = worker_id
        self.stop_event = stop_event
        self.on_task_finished = on_task_finished
        self.logger = logger

        self.thread = threading.Thread(
            target=self._run,
            name=f"NexoraWorker-{worker_id}",
            daemon=True,
        )

        self.current_task: Task | None = None

    def start(self) -> None:
        self.thread.start()

    def join(self, timeout: float | None = None) -> None:
        self.thread.join(timeout)

    def is_alive(self) -> bool:
        return self.thread.is_alive()

    def _run(self) -> None:
        ThreadContext.initialize_worker()

        while True:
            try:
                _, _, task = self.task_queue.get(timeout=0.1)
            except queue.Empty:
                if self.stop_event.is_set():
                    break
                continue

            try:
                if task is None:
                    return

                self.current_task = task

                if task.future.cancelled():
                    task.status = TaskStatus.CANCELLED
                    continue

                if not task.future._set_running():
                    if task.future.cancelled():
                        task.status = TaskStatus.CANCELLED
                    continue

                task.status = TaskStatus.RUNNING
                task.started_at = time.perf_counter()

                try:
                    result = task.function(
                        *task.args,
                        **task.kwargs,
                    )

                    task.status = TaskStatus.COMPLETED
                    task.future.set_result(result)

                except Exception as exc:
                    task.status = TaskStatus.FAILED
                    task.future.set_exception(exc)

                    if self.logger is not None:
                        self.logger.error(
                            f"Task {task.id} failed: {exc!r}"
                        )

                finally:
                    task.finished_at = time.perf_counter()

            finally:
                self.current_task = None
                self.task_queue.task_done()

                if task is not None and self.on_task_finished is not None:
                    self.on_task_finished(task)