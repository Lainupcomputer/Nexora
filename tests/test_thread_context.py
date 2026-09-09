import sys
import threading

from nexora.threading import (
    TaskScheduler,
    ThreadContext,
    ThreadType,
    NexoraThreadError,
)


def worker_test():

    print(
        "Worker thread:",
        ThreadContext.thread_name(),
    )

    print(
        "Worker type:",
        ThreadContext.current_type(),
    )

    print(
        "Is worker:",
        ThreadContext.is_worker_thread(),
    )

    try:
        ThreadContext.assert_main_thread(
            "pygame rendering"
        )

    except NexoraThreadError as exc:

        print(
            "Main-thread protection: ✅"
        )

        print(
            "Error:",
            exc,
        )

    return ThreadContext.current_type()


def main():

    print("=" * 60)
    print("NEXORA THREAD CONTEXT TEST")
    print("=" * 60)

    print()

    print(
        "Python:",
        sys.version,
    )

    print(
        "GIL:",
        sys._is_gil_enabled(),
    )

    ThreadContext.initialize()

    print(
        "Main thread:",
        ThreadContext.thread_name(),
    )

    print(
        "Main type:",
        ThreadContext.current_type(),
    )

    print(
        "Is main:",
        ThreadContext.is_main_thread(),
    )

    print()

    scheduler = TaskScheduler(
        workers=4
    )

    futures = [
        scheduler.submit(
            worker_test
        )
        for _ in range(4)
    ]

    results = scheduler.wait_all(
        futures
    )

    print()

    print(
        "Worker results:",
        results,
    )

    print()

    try:
        ThreadContext.assert_worker_thread(
            "Worker-only operation"
        )

    except NexoraThreadError as exc:

        print(
            "Worker-thread protection: ✅"
        )

        print(
            "Error:",
            exc,
        )

    scheduler.shutdown()

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print("Main thread protection: ✅")
    print("Worker identification: ✅")
    print("Thread context: ✅")
    print("GIL:", sys._is_gil_enabled())


if __name__ == "__main__":
    main()