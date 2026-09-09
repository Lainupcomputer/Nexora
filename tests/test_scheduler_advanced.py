import sys
import time
import math

from nexora.threading import (
    TaskScheduler,
    TaskPriority,
)


def calculate(task_id):

    value = task_id * 0.123456

    for i in range(500_000):
        value = (
            math.sin(value + i * 0.000001)
            + math.cos(i * 0.000002)
        )

    return task_id, value


def failing_task():

    raise ValueError(
        "Intentional Nexora test error"
    )


def main():

    print("=" * 60)
    print("NEXORA ADVANCED TASK SCHEDULER TEST")
    print("=" * 60)

    print()
    print("Python:", sys.version)
    print("GIL:", sys._is_gil_enabled())
    print()

    scheduler = TaskScheduler()

    print(
        "Workers:",
        scheduler.worker_count,
    )

    print()

    start = time.perf_counter()

    futures = []

    for i in range(20):

        future = scheduler.submit(
            calculate,
            i,
            priority=TaskPriority.NORMAL,
        )

        futures.append(future)

    # High priority tasks
    for i in range(5):

        scheduler.submit(
            calculate,
            100 + i,
            priority=TaskPriority.HIGH,
        )

    # Low priority tasks
    for i in range(5):

        scheduler.submit(
            calculate,
            200 + i,
            priority=TaskPriority.LOW,
        )

    results = scheduler.wait_all(futures)

    elapsed = (
        time.perf_counter() - start
    )

    print("Normal tasks:", len(results))
    print("Runtime:", f"{elapsed:.3f}s")

    # Exception test

    error_future = scheduler.submit(
        failing_task,
    )

    try:
        error_future.result()

    except ValueError as exc:
        print(
            "Exception handling: ✅",
            str(exc),
        )

    # Cancellation test

    cancel_future = scheduler.submit(
        calculate,
        999,
        priority=TaskPriority.LOW,
    )

    cancelled = cancel_future.cancel()

    print(
        "Cancellation:",
        "✅" if cancelled else "❌",
    )

    # Callback test

    callback_called = []

    def callback(future):

        callback_called.append(
            future.done()
        )

    callback_future = scheduler.submit(
        calculate,
        12345,
    )

    callback_future.add_done_callback(
        callback
    )

    callback_future.result()

    print(
        "Callback:",
        "✅" if callback_called else "❌",
    )

    stats = scheduler.stats()

    print()
    print("=" * 60)
    print("STATISTICS")
    print("=" * 60)

    print(
        "Total:",
        stats.total_tasks,
    )

    print(
        "Completed:",
        stats.completed_tasks,
    )

    print(
        "Failed:",
        stats.failed_tasks,
    )

    print(
        "Cancelled:",
        stats.cancelled_tasks,
    )

    print(
        "Average execution:",
        f"{stats.average_execution_time:.6f}s",
    )

    print(
        "Pending:",
        scheduler.pending_tasks(),
    )

    print(
        "Active:",
        scheduler.active_tasks(),
    )

    print(
        "Workers alive:",
        scheduler.active_workers(),
    )

    scheduler.shutdown()

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print("GIL:", sys._is_gil_enabled())
    print("Scheduler shutdown: ✅")


if __name__ == "__main__":
    main()