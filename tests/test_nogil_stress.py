import sys
import time
import threading
import math
import pygame


WORKERS = 8
TASKS_PER_WORKER = 4
ITERATIONS = 2_000_000


def cpu_task(task_id):
    """
    CPU-intensive Berechnung.
    Wichtig: Kein pygame und kein SDL innerhalb der Worker.
    """
    value = task_id * 0.123456

    for i in range(ITERATIONS):
        value = (
            math.sin(value + i * 0.000001) * 1.000001
            + math.cos(i * 0.000002)
        )

    return value


def worker(worker_id, results, lock):
    for task_index in range(TASKS_PER_WORKER):
        task_id = worker_id * TASKS_PER_WORKER + task_index

        result = cpu_task(task_id)

        with lock:
            results[task_id] = result


def main():
    print("=" * 60)
    print("NEXORA ENGINE - No-GIL Stress Test")
    print("=" * 60)
    print()

    print("Python:", sys.version)
    print("GIL vor pygame:", sys._is_gil_enabled())

    pygame.init()

    print("pygame:", pygame.version.ver)
    print("GIL nach pygame:", sys._is_gil_enabled())
    print()

    if sys._is_gil_enabled():
        print("❌ FEHLER: Der GIL ist aktiviert!")
        print()
        print("Starte stattdessen:")
        print("python -Xgil=0 test_nogil_stress.py")

        pygame.quit()
        return

    results = [0.0] * (WORKERS * TASKS_PER_WORKER)
    lock = threading.Lock()

    print("Worker:", WORKERS)
    print("Tasks pro Worker:", TASKS_PER_WORKER)
    print("Iterationen pro Task:", f"{ITERATIONS:,}")
    print("Tasks gesamt:", len(results))
    print()

    # ---------------------------------------------------------
    # pygame läuft ausschließlich im Main Thread
    # ---------------------------------------------------------

    surface = pygame.Surface((320, 180))

    start = time.perf_counter()

    threads = []

    for worker_id in range(WORKERS):
        thread = threading.Thread(
            target=worker,
            args=(worker_id, results, lock),
            name=f"NexoraWorker-{worker_id}",
        )

        threads.append(thread)
        thread.start()

    # Main Thread macht währenddessen weiterhin pygame-Arbeit
    frames = 0

    while any(thread.is_alive() for thread in threads):

        surface.fill((20, 20, 20))

        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (160, 90),
            30 + (frames % 20),
        )

        pygame.event.pump()

        frames += 1

        time.sleep(0.001)

    for thread in threads:
        thread.join()

    elapsed = time.perf_counter() - start

    checksum = sum(results)

    print()
    print("=" * 60)
    print("ERGEBNIS")
    print("=" * 60)

    print(
        "Alle Tasks abgeschlossen:",
        all(result != 0.0 for result in results),
    )

    print(
        "Main-Thread Frames:",
        f"{frames:,}",
    )

    print(
        "Checksum:",
        f"{checksum:.6f}",
    )

    print(
        "Laufzeit:",
        f"{elapsed:.3f} Sekunden",
    )

    print(
        "GIL am Ende:",
        sys._is_gil_enabled(),
    )

    print()

    if sys._is_gil_enabled():
        print("❌ Der GIL wurde während des Tests aktiviert.")

    elif all(result != 0.0 for result in results):
        print("✅ No-GIL Stress-Test erfolgreich!")
        print("✅ 8 Worker liefen parallel.")
        print("✅ pygame lief gleichzeitig im Main Thread.")
        print("✅ GIL blieb deaktiviert.")

    else:
        print("❌ Nicht alle Tasks wurden abgeschlossen.")

    pygame.quit()


if __name__ == "__main__":
    main()