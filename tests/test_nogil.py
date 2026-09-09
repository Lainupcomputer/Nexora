import sys
import time
import threading
import pygame


def work(results, index):
    total = 0

    for i in range(20_000_000):
        total += i

    results[index] = total


print("Python:", sys.version)
print("GIL vor pygame:", sys._is_gil_enabled())

pygame.init()

print("GIL nach pygame:", sys._is_gil_enabled())
print("pygame:", pygame.version.ver)

results = [None] * 4
threads = []

start = time.perf_counter()

for i in range(4):
    thread = threading.Thread(
        target=work,
        args=(results, i),
    )
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

elapsed = time.perf_counter() - start

print("Ergebnisse:", len(results))
print("Zeit:", round(elapsed, 3), "Sekunden")

pygame.quit()