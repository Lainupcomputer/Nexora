from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pygame
import sdl3

from nexora.rendering.gpu import GPUContext
from nexora.rendering.gpu.render_snapshot import RenderSnapshot
from nexora.rendering.gpu.sprite_batch import GPUSpriteBatch


WIDTH = 1280
HEIGHT = 720

WORKERS = 4

COUNTS = (
    1_000,
    5_000,
    10_000,
    25_000,
    50_000,
)


def prepare_snapshot(
    snapshot: RenderSnapshot,
    count: int,
    executor: ThreadPoolExecutor,
) -> None:

    snapshot.resize(count)

    chunk_size = (count + WORKERS - 1) // WORKERS

    futures = []

    for worker in range(WORKERS):
        start = worker * chunk_size
        end = min(start + chunk_size, count)

        if start >= end:
            continue

        futures.append(
            executor.submit(
                _prepare_range,
                snapshot,
                start,
                end,
            )
        )

    for future in futures:
        future.result()


def _prepare_range(
    snapshot: RenderSnapshot,
    start: int,
    end: int,
) -> None:

    view = memoryview(snapshot.raw).cast("f")

    for index in range(start, end):
        base = index * RenderSnapshot.FLOATS_PER_SPRITE

        x = float(index % 250) * 5.0
        y = float(index // 250) * 5.0

        view[base + 0] = x
        view[base + 1] = y

        view[base + 2] = 32.0
        view[base + 3] = 32.0

        view[base + 4] = 0.0

        view[base + 5] = 0.5
        view[base + 6] = 0.5

        view[base + 7] = 1.0

        view[base + 8] = 0.0
        view[base + 9] = 0.0

        view[base + 10] = 0.0
        view[base + 11] = 0.0

        view[base + 12] = 1.0
        view[base + 13] = 1.0


def run_test(
    batch: GPUSpriteBatch,
    snapshot: RenderSnapshot,
    executor: ThreadPoolExecutor,
    count: int,
    duration: float = 5.0,
):
    prepare_snapshot(
        snapshot,
        count,
        executor,
    )

    batch.submit_snapshot(snapshot)

    # Warmup
    warmup_end = time.perf_counter() + 2.0

    while time.perf_counter() < warmup_end:
        prepare_snapshot(
            snapshot,
            count,
            executor,
        )

        batch.submit_snapshot(snapshot)

        batch.render()

        pygame.event.pump()

    frames = 0
    prep_total = 0.0

    start_time = time.perf_counter()
    end_time = start_time + duration

    while time.perf_counter() < end_time:
        prep_start = time.perf_counter()

        prepare_snapshot(
            snapshot,
            count,
            executor,
        )

        prep_time = time.perf_counter() - prep_start
        prep_total += prep_time

        batch.submit_snapshot(snapshot)

        batch.render()

        pygame.event.pump()

        frames += 1

    total = time.perf_counter() - start_time

    fps = frames / total
    frame_ms = 1000.0 / fps
    prep_ms = (prep_total / frames) * 1000.0
    rest_ms = max(frame_ms - prep_ms, 0.0)

    return fps, frame_ms, prep_ms, rest_ms


def main():
    print()
    print("=" * 72)
    print("NEXORA GPU SPRITE BENCHMARK - DIRECT SNAPSHOT")
    print("=" * 72)
    print()

    print("Python:", __import__("sys").version.split()[0])
    print(
        "GIL enabled:",
        __import__("sys")._is_gil_enabled(),
    )
    print(f"Resolution:   {WIDTH}x{HEIGHT}")
    print("Warmup:       2.0s")
    print("Benchmark:    5.0s")
    print("VSync:        OFF")
    print(f"Workers:      {WORKERS}")
    print()

    pygame.init()

    context = GPUContext(
        WIDTH,
        HEIGHT,
        "Nexora Snapshot Benchmark",
        debug=True,
        frames_in_flight=2,
        vsync=False,
    )

    batch = GPUSpriteBatch(
        context,
        max_sprites=max(COUNTS),
    )

    snapshot = RenderSnapshot(
        max(COUNTS)
    )

    executor = ThreadPoolExecutor(
        max_workers=WORKERS,
        thread_name_prefix="snapshot",
    )

    print("GPU backend:", context.driver)
    print("SpriteBatch: OK")
    print("RenderSnapshot: OK")
    print()

    print("=" * 72)
    print("RUNNING DIRECT SNAPSHOT BENCHMARK")
    print("=" * 72)
    print()

    print(
        f"{'Sprites':>12} | "
        f"{'FPS':>10} | "
        f"{'Frame ms':>10} | "
        f"{'CPU prep':>10} | "
        f"{'GPU/rest':>10}"
    )

    print("-" * 72)

    try:
        for count in COUNTS:
            print(f"Preparing {count:,} sprites...")

            fps, frame_ms, prep_ms, rest_ms = run_test(
                batch,
                snapshot,
                executor,
                count,
            )

            print(
                f"{count:>12,} | "
                f"{fps:>10.2f} | "
                f"{frame_ms:>10.3f} | "
                f"{prep_ms:>10.3f} | "
                f"{rest_ms:>10.3f}"
            )

    finally:
        executor.shutdown(
            wait=True,
            cancel_futures=True,
        )

        batch.destroy()
        context.destroy()

        pygame.quit()

    print()
    print("=" * 72)
    print("BENCHMARK COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()