from __future__ import annotations

import random
import time
from pathlib import Path

import pygame
import sdl3

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.texture import GPUTexture
from nexora.rendering.gpu.sprite_batch import GPUSpriteBatch


# ============================================================
# CONFIG
# ============================================================

WIDTH = 1280
HEIGHT = 720

WARMUP_SECONDS = 2.0
BENCHMARK_SECONDS = 5.0

SPRITE_COUNTS = [
    1_000,
    5_000,
    10_000,
    25_000,
    50_000,
]

WORKERS = 4

ROOT = Path(__file__).resolve().parent.parent

VERTEX_SHADER = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
    / "sprite.vert.spv"
)

FRAGMENT_SHADER = (
    ROOT
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
    / "sprite.frag.spv"
)


# ============================================================
# HELPERS
# ============================================================

def make_sprites(count: int):
    """
    Create all sprite descriptions once.

    Sprite creation is NOT part of the benchmark.
    """

    rng = random.Random(1337)

    sprites = []

    for _ in range(count):
        x = rng.uniform(
            -1000.0,
            1000.0,
        )

        y = rng.uniform(
            -600.0,
            600.0,
        )

        rotation = rng.uniform(
            0.0,
            6.283185307179586,
        )

        sprites.append(
            (
                x,
                y,
                32.0,
                32.0,
                rotation,
                0.5,
                0.5,
                1.0,
                False,
                False,
                0.0,
                0.0,
                1.0,
                1.0,
            )
        )

    return sprites


def handle_events():
    """
    Return False when the user closes the benchmark.
    """

    event = sdl3.SDL_Event()

    while sdl3.SDL_PollEvent(event):
        event_type = event.type

        if event_type == sdl3.SDL_EVENT_QUIT:
            return False

    return True


# ============================================================
# BENCHMARK
# ============================================================

def benchmark_batch(
    context,
    texture,
    batch,
    sprites,
    duration,
):
    """
    Benchmark one sprite count.

    Returns:

        fps
        frame_ms
        cpu_prepare_ms
        gpu_frame_ms
    """

    running = True

    # --------------------------------------------------------
    # Warmup
    # --------------------------------------------------------

    warmup_start = time.perf_counter()

    while (
        running
        and time.perf_counter()
        - warmup_start
        < WARMUP_SECONDS
    ):
        running = handle_events()

        batch.begin(texture)

        batch.add_many(
            sprites,
            workers=WORKERS,
        )

        batch.end()

    if not running:
        return None

    # --------------------------------------------------------
    # Benchmark
    # --------------------------------------------------------

    frame_count = 0

    total_frame_time = 0.0
    total_prepare_time = 0.0

    benchmark_start = time.perf_counter()

    while (
        running
        and time.perf_counter()
        - benchmark_start
        < duration
    ):
        frame_start = time.perf_counter()

        running = handle_events()

        if not running:
            break

        batch.begin(texture)

        # ----------------------------------------------------
        # CPU preparation
        # ----------------------------------------------------

        prepare_start = time.perf_counter()

        batch.add_many(
            sprites,
            workers=WORKERS,
        )

        prepare_end = time.perf_counter()

        # ----------------------------------------------------
        # Upload + GPU render + submit
        # ----------------------------------------------------

        batch.end()

        frame_end = time.perf_counter()

        prepare_ms = (
            prepare_end
            - prepare_start
        ) * 1000.0

        frame_ms = (
            frame_end
            - frame_start
        ) * 1000.0

        total_prepare_time += prepare_ms
        total_frame_time += frame_ms

        frame_count += 1

    if frame_count == 0:
        return None

    elapsed = (
        time.perf_counter()
        - benchmark_start
    )

    fps = frame_count / elapsed

    avg_frame_ms = (
        total_frame_time
        / frame_count
    )

    avg_prepare_ms = (
        total_prepare_time
        / frame_count
    )

    gpu_frame_ms = max(
        0.0,
        avg_frame_ms
        - avg_prepare_ms,
    )

    return (
        fps,
        avg_frame_ms,
        avg_prepare_ms,
        gpu_frame_ms,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 72)
    print("NEXORA GPU SPRITE BENCHMARK - PARALLEL")
    print("=" * 72)
    print()

    print(
        f"Python:       {__import__('sys').version.split()[0]}"
    )

    try:
        import sys

        gil_enabled = sys._is_gil_enabled()

    except AttributeError:
        gil_enabled = True

    print(
        f"GIL enabled:  {gil_enabled}"
    )

    print(
        f"Resolution:   {WIDTH}x{HEIGHT}"
    )

    print(
        f"Warmup:       {WARMUP_SECONDS:.1f}s"
    )

    print(
        f"Benchmark:    {BENCHMARK_SECONDS:.1f}s"
    )

    print(
        "VSync:        OFF"
    )

    print(
        f"Workers:      {WORKERS}"
    )

    print()

    print("Sprite counts:")

    for count in SPRITE_COUNTS:
        print(
            f"  {count:,}"
        )

    print()

    print("Vertex shader:")
    print(
        f"  {VERTEX_SHADER}"
    )

    print("Fragment shader:")
    print(
        f"  {FRAGMENT_SHADER}"
    )

    print()

    context = None
    texture = None
    batch = None

    results = []

    try:
        # ====================================================
        # GPU CONTEXT
        # ====================================================

        context = GPUContext(
            WIDTH,
            HEIGHT,
            "Nexora GPU Parallel Benchmark",
            debug=True,
            frames_in_flight=2,
            vsync=False,
        )

        print(
            f"GPU backend:  {context.driver}"
        )

        # ====================================================
        # TEST TEXTURE
        # ====================================================

        # 4 colored pixels:
        #
        # red / green
        # blue / white

        pixels = bytes(
            [
                255, 0, 0, 255,
                0, 255, 0, 255,

                0, 0, 255, 255,
                255, 255, 255, 255,
            ]
        )

        texture = GPUTexture(
            context.device,
            2,
            2,
            data=pixels,
        )

        print(
            "Texture:      OK"
        )

        # ====================================================
        # SPRITE BATCH
        # ====================================================

        batch = GPUSpriteBatch(
            context,
            max_sprites=50_000,
            vertex_shader_path=VERTEX_SHADER,
            fragment_shader_path=FRAGMENT_SHADER,
            workers=WORKERS,
        )

        print(
            "SpriteBatch:  OK"
        )

        print()

        print("=" * 72)
        print("RUNNING PARALLEL BENCHMARK")
        print("=" * 72)
        print()

        # ====================================================
        # RUN COUNTS
        # ====================================================

        for count in SPRITE_COUNTS:
            print(
                f"Preparing {count:,} sprites..."
            )

            sprites = make_sprites(
                count
            )

            result = benchmark_batch(
                context,
                texture,
                batch,
                sprites,
                BENCHMARK_SECONDS,
            )

            if result is None:
                print(
                    "Benchmark cancelled."
                )

                break

            (
                fps,
                frame_ms,
                prepare_ms,
                gpu_ms,
            ) = result

            results.append(
                (
                    count,
                    fps,
                    frame_ms,
                    prepare_ms,
                    gpu_ms,
                )
            )

            print(
                f"{count:>8,} sprites | "
                f"{fps:>9.2f} FPS | "
                f"{frame_ms:>8.3f} ms | "
                f"CPU prep: {prepare_ms:>7.3f} ms | "
                f"GPU/rest: {gpu_ms:>7.3f} ms"
            )

            print()

        # ====================================================
        # RESULTS
        # ====================================================

        print("=" * 72)
        print("RESULTS")
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

        for (
            count,
            fps,
            frame_ms,
            prepare_ms,
            gpu_ms,
        ) in results:

            print(
                f"{count:>12,} | "
                f"{fps:>10.2f} | "
                f"{frame_ms:>10.3f} | "
                f"{prepare_ms:>10.3f} | "
                f"{gpu_ms:>10.3f}"
            )

        print()

        print("=" * 72)
        print("BENCHMARK COMPLETE")
        print("=" * 72)

    except KeyboardInterrupt:
        print()
        print(
            "Benchmark interrupted."
        )

    finally:
        print()
        print(
            "Shutting down..."
        )

        if batch:
            batch.destroy()

        if texture:
            texture.destroy()

        if context:
            context.destroy()

        print(
            "Done."
        )


if __name__ == "__main__":
    main()