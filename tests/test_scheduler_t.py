from __future__ import annotations

import sys
import threading
import time
import threading
import time

from nexora.threading.future import FutureStatus

from nexora.threading import (
    FutureStatus,
    TaskPriority,
    TaskScheduler,
)


WORKERS = 8


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

    print(f"✅ {message}")


def cpu_work(iterations: int) -> int:
    value = 0

    for i in range(iterations):
        value += (i * 31) % 997

    return value


def test_basic_tasks(scheduler: TaskScheduler) -> None:
    section("1. BASIC TASKS")

    futures = [
        scheduler.submit(lambda value=value: value * 2)
        for value in range(20)
    ]

    results = scheduler.wait_all(futures)

    check(
        results == [i * 2 for i in range(20)],
        "20 tasks completed with correct results",
    )

    check(
        all(future.done() for future in futures),
        "All futures report done()",
    )

    check(
        all(future.status is FutureStatus.COMPLETED for future in futures),
        "All futures have COMPLETED status",
    )


def test_future_states(scheduler: TaskScheduler) -> None:
    section("2. FUTURE STATES")

    started = threading.Event()
    release = threading.Event()

    def blocking_task():
        started.set()
        release.wait()
        return 123

    future = scheduler.submit(blocking_task)

    check(
        started.wait(timeout=2.0),
        "Blocking task started",
    )

    check(
        future.running(),
        "running() is True while task is executing",
    )

    check(
        not future.pending(),
        "pending() is False while task is executing",
    )

    release.set()

    check(
        future.result(timeout=2.0) == 123,
        "Running future returned correct result",
    )

    check(
        future.status is FutureStatus.COMPLETED,
        "Future transitioned to COMPLETED",
    )


def test_cancellation(scheduler):
    print()
    print("=" * 70)
    print("3. CANCELLATION")
    print("=" * 70)

    worker_count = scheduler.worker_count

    # Alle Worker blockieren.
    blocker_started = threading.Event()
    release_blockers = threading.Event()

    def blocker():
        blocker_started.set()
        release_blockers.wait(timeout=10.0)
        return "released"

    blockers = [
        scheduler.submit(blocker)
        for _ in range(worker_count)
    ]

    # Warten, bis mindestens ein Worker wirklich blockiert.
    deadline = time.perf_counter() + 5.0

    while scheduler.active_tasks() < worker_count:
        if time.perf_counter() >= deadline:
            release_blockers.set()
            scheduler.wait_all(blockers)
            raise AssertionError("Not all workers became occupied.")

        time.sleep(0.001)

    print("✅ All workers are occupied")

    # Jetzt liegen diese Tasks garantiert hinter den blockierenden Tasks
    # in der Queue und können nicht sofort ausgeführt werden.
    pending_count = 10

    pending = [
        scheduler.submit(lambda: "should not execute")
        for _ in range(pending_count)
    ]

    cancelled = scheduler.cancel_all_pending()

    assert cancelled == pending_count, (
        f"Expected {pending_count} cancelled tasks, "
        f"got {cancelled}"
    )

    print(f"✅ {pending_count} pending futures cancelled")

    for future in pending:
        assert future.cancelled()
        assert future.done()
        assert future.status is FutureStatus.CANCELLED

    print("✅ All cancelled futures report cancelled()")
    print("✅ All cancelled futures have CANCELLED status")

    # Blocker freigeben.
    release_blockers.set()

    results = scheduler.wait_all(blockers)

    assert results == ["released"] * worker_count

    print("✅ All blocker tasks completed")
def test_exceptions(scheduler: TaskScheduler) -> None:
    section("4. EXCEPTIONS")

    def broken_task():
        raise ValueError("intentional test error")

    future = scheduler.submit(broken_task)

    try:
        future.result(timeout=2.0)
    except ValueError as exc:
        check(
            str(exc) == "intentional test error",
            "Exception propagated through Future",
        )
    else:
        raise AssertionError(
            "Future.result() did not raise the task exception."
        )

    check(
        future.status is FutureStatus.FAILED,
        "Failed task has FAILED status",
    )

    check(
        isinstance(future.exception(), ValueError),
        "Future.exception() contains the original exception",
    )


def test_callbacks(scheduler: TaskScheduler) -> None:
    section("5. CALLBACKS")

    callback_called = threading.Event()
    callback_future = {"value": None}

    def callback(future):
        callback_future["value"] = future.result()
        callback_called.set()

    future = scheduler.submit(lambda: 42)
    future.add_done_callback(callback)

    check(
        future.result(timeout=2.0) == 42,
        "Callback test task completed",
    )

    check(
        callback_called.wait(timeout=2.0),
        "Done callback executed",
    )

    check(
        callback_future["value"] == 42,
        "Callback received correct Future",
    )


def test_wait_any(scheduler: TaskScheduler) -> None:
    section("6. WAIT ANY")

    first = threading.Event()

    def slow():
        time.sleep(0.2)
        return "slow"

    def fast():
        first.set()
        return "fast"

    futures = [
        scheduler.submit(slow),
        scheduler.submit(fast),
    ]

    completed = scheduler.wait_any(
        futures,
        timeout=2.0,
    )

    check(
        completed is not None,
        "wait_any() returned a Future",
    )

    check(
        completed.result() == "fast",
        "wait_any() returned the first completed task",
    )

    # Make sure the slow task is finished before the next test.
    scheduler.wait_all(futures)


def test_priority(scheduler: TaskScheduler) -> None:
    section("7. PRIORITY")

    # Priority is tested by filling the worker pool first.
    gate = threading.Event()
    started_count = 0
    started_lock = threading.Lock()
    all_started = threading.Event()

    def blocker():
        nonlocal started_count

        with started_lock:
            started_count += 1

            if started_count == WORKERS:
                all_started.set()

        gate.wait()

    blockers = [
        scheduler.submit(
            blocker,
            priority=TaskPriority.NORMAL,
        )
        for _ in range(WORKERS)
    ]

    check(
        all_started.wait(timeout=2.0),
        "Worker pool filled for priority test",
    )

    execution_order = []
    order_lock = threading.Lock()

    def record(name):
        with order_lock:
            execution_order.append(name)

    low = scheduler.submit(
        record,
        "LOW",
        priority=TaskPriority.LOW,
    )

    high = scheduler.submit(
        record,
        "HIGH",
        priority=TaskPriority.HIGH,
    )

    normal = scheduler.submit(
        record,
        "NORMAL",
        priority=TaskPriority.NORMAL,
    )

    gate.set()

    scheduler.wait_all(
        blockers + [low, high, normal]
    )

    check(
        set(execution_order) == {"LOW", "HIGH", "NORMAL"},
        "All priority tasks executed",
    )

    check(
        execution_order.index("HIGH")
        < execution_order.index("LOW"),
        "HIGH priority executed before LOW priority",
    )


def test_parallel_cpu_work(scheduler: TaskScheduler) -> None:
    section("8. PARALLEL CPU WORK")

    task_count = WORKERS * 2

    start = time.perf_counter()

    futures = [
        scheduler.submit(
            cpu_work,
            2_000_000,
            priority=TaskPriority.NORMAL,
        )
        for _ in range(task_count)
    ]

    results = scheduler.wait_all(futures)

    elapsed = time.perf_counter() - start

    check(
        len(results) == task_count,
        f"{task_count} CPU tasks completed",
    )

    check(
        all(isinstance(result, int) for result in results),
        "All CPU tasks returned valid results",
    )

    print(f"Runtime: {elapsed:.3f}s")
    print(f"Workers: {scheduler.worker_count}")


def test_cancel_all_pending(scheduler: TaskScheduler) -> None:
    section("9. CANCEL ALL PENDING")

    gate = threading.Event()
    started = threading.Event()

    def blocking():
        started.set()
        gate.wait()

    running = scheduler.submit(
        blocking,
        priority=TaskPriority.HIGH,
    )

    check(
        started.wait(timeout=2.0),
        "Blocking task started",
    )

    futures = [
        scheduler.submit(lambda: None)
        for _ in range(20)
    ]

    cancelled = scheduler.cancel_all_pending()

    check(
        cancelled >= 1,
        f"cancel_all_pending() cancelled {cancelled} tasks",
    )

    gate.set()

    running.result(timeout=2.0)

    scheduler.wait_all(
        [
            future
            for future in futures
            if not future.cancelled()
        ]
    )


def test_statistics(scheduler: TaskScheduler) -> None:
    section("10. STATISTICS")

    stats = scheduler.stats()

    print(f"Total:       {stats.total_tasks}")
    print(f"Completed:   {stats.completed_tasks}")
    print(f"Failed:      {stats.failed_tasks}")
    print(f"Cancelled:   {stats.cancelled_tasks}")
    print(f"Execution:   {stats.total_execution_time:.6f}s")
    print(f"Average:     {stats.average_execution_time:.6f}s")

    check(
        stats.total_tasks > 0,
        "Scheduler recorded submitted tasks",
    )

    check(
        stats.completed_tasks > 0,
        "Scheduler recorded completed tasks",
    )

    check(
        stats.failed_tasks > 0,
        "Scheduler recorded failed tasks",
    )

    check(
        stats.cancelled_tasks > 0,
        "Scheduler recorded cancelled tasks",
    )


def test_shutdown(scheduler: TaskScheduler) -> None:
    section("11. SHUTDOWN")

    scheduler.shutdown(wait=True)

    check(
        scheduler.shutdown_requested,
        "Scheduler reports shutdown requested",
    )

    check(
        scheduler.active_workers() == 0,
        "All workers stopped",
    )

    try:
        scheduler.submit(lambda: None)
    except RuntimeError:
        print("✅ Submit after shutdown correctly rejected")
    else:
        raise AssertionError(
            "Scheduler accepted task after shutdown."
        )


def main() -> None:
    section("NEXORA TASK SCHEDULER TEST")

    print(f"Python:   {sys.version.split()[0]}")
    print(f"GIL:      {sys._is_gil_enabled()}")
    print(f"Workers:  {WORKERS}")

    check(
        sys._is_gil_enabled() is False,
        "Python is running with the GIL disabled",
    )

    scheduler = TaskScheduler(workers=WORKERS)

    try:
        test_basic_tasks(scheduler)
        test_future_states(scheduler)
        test_cancellation(scheduler)
        test_exceptions(scheduler)
        test_callbacks(scheduler)
        test_wait_any(scheduler)
        test_priority(scheduler)
        test_parallel_cpu_work(scheduler)
        test_cancel_all_pending(scheduler)
        test_statistics(scheduler)
    finally:
        if not scheduler.shutdown_requested:
            scheduler.shutdown(wait=True)

    check(
        scheduler.active_workers() == 0,
        "Final worker count is zero",
    )

    section("TEST COMPLETE")
    print("ALL SCHEDULER TESTS PASSED")


if __name__ == "__main__":
    main()