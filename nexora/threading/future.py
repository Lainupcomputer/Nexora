from __future__ import annotations

import threading
from enum import Enum
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class FutureStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Future(Generic[T]):
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._status = FutureStatus.PENDING
        self._result: T | None = None
        self._exception: BaseException | None = None
        self._callbacks: list[Callable[["Future[T]"], None]] = []

    def _set_running(self) -> bool:
        with self._condition:
            if self._status is not FutureStatus.PENDING:
                return False
            self._status = FutureStatus.RUNNING
            return True

    def set_result(self, result: T) -> None:
        with self._condition:
            if self._status not in (FutureStatus.PENDING, FutureStatus.RUNNING):
                raise RuntimeError("Future is already completed.")

            self._result = result
            self._status = FutureStatus.COMPLETED
            callbacks = self._callbacks
            self._callbacks = []
            self._condition.notify_all()

        self._run_callbacks(callbacks)

    def set_exception(self, exception: BaseException) -> None:
        with self._condition:
            if self._status not in (FutureStatus.PENDING, FutureStatus.RUNNING):
                raise RuntimeError("Future is already completed.")

            self._exception = exception
            self._status = FutureStatus.FAILED
            callbacks = self._callbacks
            self._callbacks = []
            self._condition.notify_all()

        self._run_callbacks(callbacks)

    def cancel(self) -> bool:
        with self._condition:
            if self._status is not FutureStatus.PENDING:
                return False

            self._status = FutureStatus.CANCELLED
            callbacks = self._callbacks
            self._callbacks = []
            self._condition.notify_all()

        self._run_callbacks(callbacks)
        return True

    def cancelled(self) -> bool:
        with self._condition:
            return self._status is FutureStatus.CANCELLED

    def done(self) -> bool:
        with self._condition:
            return self._status in (
                FutureStatus.COMPLETED,
                FutureStatus.FAILED,
                FutureStatus.CANCELLED,
            )

    def running(self) -> bool:
        with self._condition:
            return self._status is FutureStatus.RUNNING

    def pending(self) -> bool:
        with self._condition:
            return self._status is FutureStatus.PENDING

    @property
    def status(self) -> FutureStatus:
        with self._condition:
            return self._status

    def wait(self, timeout: float | None = None) -> bool:
        with self._condition:
            completed = self._status in (
                FutureStatus.COMPLETED,
                FutureStatus.FAILED,
                FutureStatus.CANCELLED,
            )

            if not completed:
                self._condition.wait_for(
                    lambda: self._status in (
                        FutureStatus.COMPLETED,
                        FutureStatus.FAILED,
                        FutureStatus.CANCELLED,
                    ),
                    timeout=timeout,
                )

            return self._status in (
                FutureStatus.COMPLETED,
                FutureStatus.FAILED,
                FutureStatus.CANCELLED,
            )

    def result(self, timeout: float | None = None) -> T:
        if not self.wait(timeout):
            raise TimeoutError("Future result timed out.")

        with self._condition:
            if self._status is FutureStatus.CANCELLED:
                raise RuntimeError("Future was cancelled.")

            if self._status is FutureStatus.FAILED:
                assert self._exception is not None
                raise self._exception

            return self._result  # type: ignore[return-value]

    def exception(
        self,
        timeout: float | None = None,
    ) -> BaseException | None:
        if not self.wait(timeout):
            raise TimeoutError("Future exception timed out.")

        with self._condition:
            return self._exception

    def add_done_callback(
        self,
        callback: Callable[["Future[T]"], None],
    ) -> None:
        with self._condition:
            if self._status in (
                FutureStatus.COMPLETED,
                FutureStatus.FAILED,
                FutureStatus.CANCELLED,
            ):
                run_now = True
            else:
                self._callbacks.append(callback)
                run_now = False

        if run_now:
            try:
                callback(self)
            except Exception:
                pass

    def _run_callbacks(
        self,
        callbacks: list[Callable[["Future[T]"], None]],
    ) -> None:
        for callback in callbacks:
            try:
                callback(self)
            except Exception:
                pass