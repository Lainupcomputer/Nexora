import sys
import time
import math
import threading

from nexora.threading import TaskScheduler


def heavy_calculation(task_id):
    value = task_id * 0.123456

    for i in range(2_000_000):
        value = (
            math.sin(value + i * 0.000001)
            + math.cos(i * 0.000002)
        )

    return task_id, value


def main():

    print("=" * 60)
    print("NEXORA TASK SCHEDULER TEST")
    print("=" * 60)

    print()
    print("Python:", sys.version)
    print("GIL:", sys._is_gil_enabled())
    print()

    scheduler = TaskScheduler()

    print("CPU cores:", scheduler.worker_count + 1)
    print("Worker:", scheduler.worker_count)
    print()

    start = time.perf_counter()

    futures = []

    for task_id in range(
        scheduler.worker_count * 2
    ):
        future = scheduler.submit(
            heavy_calculation,
            task_id,
        )

        futures.append(future)

    print(
        "Tasks submitted:",
        len(futures),
    )

    results = scheduler.wait_all(
        futures
    )

    elapsed = time.perf_counter() - start

    print()
    print("Results:", len(results))
    print("Runtime:", f"{elapsed:.3f}s")
    print(
        "Active workers:",
        scheduler.active_workers(),
    )

    scheduler.shutdown()

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    if len(results) == len(futures):
        print("✅ All tasks completed")
    else:
        print("❌ Missing tasks")

    print(
        "GIL at end:",
        sys._is_gil_enabled(),
    )

    print()
    print("Scheduler shutdown complete.")


if __name__ == "__main__":
    main()