from __future__ import annotations

import sys
import threading
import time

import pytest

from nexora.threading import (
    FutureStatus,
    TaskPriority,
    TaskScheduler,
    ThreadContext,
    ThreadType,
)


def test_main_thread_context():
    assert ThreadContext.is_main_thread()
    assert not ThreadContext.is_worker_thread()
    assert ThreadContext.current_type() is ThreadType.MAIN


def test_worker_thread_context(scheduler):
    def worker():
        return (
            ThreadContext.current_type(),
            ThreadContext.is_worker_thread(),
            ThreadContext.is_main_thread(),
            ThreadContext.thread_name(),
        )

    futures = [
        scheduler.submit(worker)
        for _ in range(4)
    ]

    results = scheduler.wait_all(futures)

    assert len(results) == 4

    for thread_type, is_worker, is_main, name in results:
        assert thread_type is ThreadType.WORKER
        assert is_worker is True
        assert is_main is False
        assert name.startswith("NexoraWorker-")


def test_task_result(scheduler):
    future = scheduler.submit(lambda: 21 * 2)

    assert future.result(timeout=2.0) == 42
    assert future.done()
    assert future.status is FutureStatus.COMPLETED


def test_task_exception(scheduler):
    def failing_task():
        raise ValueError("test error")

    future = scheduler.submit(failing_task)

    with pytest.raises(ValueError, match="test error"):
        future.result(timeout=2.0)

    assert future.status is FutureStatus.FAILED
    assert isinstance(future.exception(), ValueError)


def test_task_cancellation(scheduler):
    started = threading.Event()
    release = threading.Event()

    def blocker():
        started.set()
        release.wait(timeout=5.0)

    running = scheduler.submit(blocker)

    assert started.wait(timeout=2.0)

    pending = [
        scheduler.submit(lambda: None)
        for _ in range(10)
    ]

    cancelled = scheduler.cancel_all_pending()

    assert cancelled >= 1

    for future in pending:
        if future.cancelled():
            assert future.done()
            assert future.status is FutureStatus.CANCELLED

    release.set()
    running.result(timeout=2.0)


def test_parallel_cpu_execution(scheduler):
    """
    Verifies that multiple CPU-heavy tasks can actually run
    on different worker threads.

    This test is particularly relevant for Python 3.13t.
    """

    thread_ids = set()
    lock = threading.Lock()

    def cpu_task():
        total = 0

        for i in range(500_000):
            total += (i * 31) % 997

        with lock:
            thread_ids.add(threading.get_ident())

        return total

    futures = [
        scheduler.submit(
            cpu_task,
            priority=TaskPriority.NORMAL,
        )
        for _ in range(8)
    ]

    results = scheduler.wait_all(futures)

    assert len(results) == 8
    assert all(isinstance(result, int) for result in results)

    # With multiple workers we expect more than one worker thread
    # to have executed the CPU workload.
    assert len(thread_ids) >= 2


def test_free_threading():
    assert hasattr(sys, "_is_gil_enabled")
    assert sys._is_gil_enabled() is False


def test_scheduler_shutdown():
    scheduler = TaskScheduler(workers=2)

    scheduler.submit(lambda: 42).result(timeout=2.0)

    scheduler.shutdown(wait=True)

    assert scheduler.shutdown_requested
    assert scheduler.active_workers() == 0

    with pytest.raises(RuntimeError):
        scheduler.submit(lambda: None)