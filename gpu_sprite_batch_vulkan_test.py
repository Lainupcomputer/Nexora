from __future__ import annotations
import os

os.environ["SDL_GPU_DRIVER"] = "vulkan"

import math
import random
import sys
import time
from pathlib import Path

import pygame
import sdl3

from nexora.rendering.camera import Camera
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.texture import GPUTexture
from nexora.rendering.gpu.sprite_batch import GPUSpriteBatch


# ============================================================
# CONFIG
# ============================================================

WIDTH = 1280
HEIGHT = 720

BENCHMARK_SPRITE_COUNTS = (
    1_000,
    5_000,
    10_000,
    25_000,
    50_000,
)

WARMUP_SECONDS = 2.0
BENCHMARK_SECONDS = 5.0

SHADER_DIR = (
    Path(__file__).resolve().parent.parent
    / "nexora"
    / "rendering"
    / "shaders"
    / "bin"
)

VERTEX_SHADER = (
    SHADER_DIR
    / "sprite.vert.spv"
)

FRAGMENT_SHADER = (
    SHADER_DIR
    / "sprite.frag.spv"
)


# ============================================================
# TEST TEXTURE
# ============================================================

def create_test_texture_data():
    """
    Creates a 64x64 RGBA test texture.

    Four colored quadrants make rotation, UVs and filtering
    easy to see.
    """

    pygame.init()

    surface = pygame.Surface(
        (64, 64),
        pygame.SRCALPHA,
    )

    # Top-left
    pygame.draw.rect(
        surface,
        (255, 80, 80, 255),
        (0, 0, 32, 32),
    )

    # Top-right
    pygame.draw.rect(
        surface,
        (80, 255, 80, 255),
        (32, 0, 32, 32),
    )

    # Bottom-left
    pygame.draw.rect(
        surface,
        (80, 120, 255, 255),
        (0, 32, 32, 32),
    )

    # Bottom-right
    pygame.draw.rect(
        surface,
        (255, 220, 80, 255),
        (32, 32, 32, 32),
    )

    return pygame.image.tobytes(
        surface,
        "RGBA",
        False,
    )


# ============================================================
# SPRITE GENERATION
# ============================================================

def generate_sprites(
    count: int,
    *,
    seed: int = 1337,
):
    """
    Generate deterministic sprite data.

    Returning a list once and reusing it keeps the benchmark
    focused on rendering rather than random-number generation.
    """

    rng = random.Random(seed)

    sprites = []

    for _ in range(count):
        x = rng.uniform(
            -WIDTH * 0.5,
            WIDTH * 0.5,
        )

        y = rng.uniform(
            -HEIGHT * 0.5,
            HEIGHT * 0.5,
        )

        width = rng.uniform(
            24.0,
            64.0,
        )

        height = rng.uniform(
            24.0,
            64.0,
        )

        rotation = rng.uniform(
            0.0,
            math.tau,
        )

        sprites.append(
            (
                x,
                y,
                width,
                height,
                rotation,
            )
        )

    return sprites


# ============================================================
# FRAME RENDER
# ============================================================

def render_frame(
    batch: GPUSpriteBatch,
    texture: GPUTexture,
    sprites,
):
    batch.begin(texture)

    for (
        x,
        y,
        width,
        height,
        rotation,
    ) in sprites:

        batch.add(
            x,
            y,
            width,
            height,
            rotation=rotation,
            origin=(0.5, 0.5),
            alpha=1.0,
            flip_x=False,
            flip_y=False,
            uv=(
                0.0,
                0.0,
                1.0,
                1.0,
            ),
        )

    batch.end()


# ============================================================
# EVENTS
# ============================================================

def process_events(context: GPUContext):
    for event in context.poll_events():

        if event.type == sdl3.SDL_EVENT_QUIT:
            return False

        if event.type == sdl3.SDL_EVENT_KEY_DOWN:
            if event.key.scancode == sdl3.SDL_SCANCODE_ESCAPE:
                return False

    return True


# ============================================================
# BENCHMARK
# ============================================================

def run_benchmark(
    context: GPUContext,
    batch: GPUSpriteBatch,
    texture: GPUTexture,
    sprites,
    sprite_count: int,
):
    print()
    print(
        f"Preparing {sprite_count:,} sprites..."
    )

    # --------------------------------------------------------
    # Warmup
    # --------------------------------------------------------

    warmup_start = time.perf_counter()

    warmup_frames = 0

    while (
        time.perf_counter() - warmup_start
        < WARMUP_SECONDS
    ):
        if not process_events(context):
            return None

        render_frame(
            batch,
            texture,
            sprites,
        )

        warmup_frames += 1

    # --------------------------------------------------------
    # Benchmark
    # --------------------------------------------------------

    benchmark_start = time.perf_counter()

    frames = 0

    while (
        time.perf_counter() - benchmark_start
        < BENCHMARK_SECONDS
    ):
        if not process_events(context):
            return None

        render_frame(
            batch,
            texture,
            sprites,
        )

        frames += 1

    elapsed = (
        time.perf_counter()
        - benchmark_start
    )

    fps = (
        frames / elapsed
        if elapsed > 0.0
        else 0.0
    )

    frame_ms = (
        1000.0 / fps
        if fps > 0.0
        else 0.0
    )

    return {
        "sprites": sprite_count,
        "frames": frames,
        "seconds": elapsed,
        "fps": fps,
        "frame_ms": frame_ms,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 72)
    print("NEXORA GPU SPRITE BENCHMARK")
    print("=" * 72)

    print()
    print(
        f"Python:       {sys.version.split()[0]}"
    )

    if hasattr(sys, "_is_gil_enabled"):
        print(
            f"GIL enabled:  {sys._is_gil_enabled()}"
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
        f"VSync:        OFF"
    )

    print()
    print(
        "Sprite counts:"
    )

    for count in BENCHMARK_SPRITE_COUNTS:
        print(
            f"  {count:,}"
        )

    print()
    print(
        "Vertex shader:"
    )
    print(
        f"  {VERTEX_SHADER}"
    )

    print(
        "Fragment shader:"
    )
    print(
        f"  {FRAGMENT_SHADER}"
    )

    if not VERTEX_SHADER.exists():
        raise FileNotFoundError(
            f"Vertex shader not found:\n"
            f"{VERTEX_SHADER}"
        )

    if not FRAGMENT_SHADER.exists():
        raise FileNotFoundError(
            f"Fragment shader not found:\n"
            f"{FRAGMENT_SHADER}"
        )

    pygame.init()

    context = None
    texture = None
    batch = None

    results = []

    try:
        # ----------------------------------------------------
        # GPU
        # ----------------------------------------------------

        context = GPUContext(
            WIDTH,
            HEIGHT,
            "Nexora GPU Benchmark",
            debug=False,
            frames_in_flight=3,
            vsync=False,
        )

        print()
        print(
            f"GPU backend:  {context.driver}"
        )

        # ----------------------------------------------------
        # Texture
        # ----------------------------------------------------

        texture_data = (
            create_test_texture_data()
        )

        texture = GPUTexture(
            context.device,
            64,
            64,
            data=texture_data,
        )

        print(
            "Texture:      OK"
        )

        # ----------------------------------------------------
        # Camera
        # ----------------------------------------------------

        camera = Camera()

        camera.x = 0.0
        camera.y = 0.0
        camera.zoom = 1.0

        # ----------------------------------------------------
        # Sprite batch
        # ----------------------------------------------------

        maximum = max(
            BENCHMARK_SPRITE_COUNTS
        )

        batch = GPUSpriteBatch(
            context,
            vertex_shader_path=VERTEX_SHADER,
            fragment_shader_path=FRAGMENT_SHADER,
            camera=camera,
            max_sprites=maximum,
        )

        print(
            "SpriteBatch:  OK"
        )

        print()
        print("=" * 72)
        print(
            "RUNNING BENCHMARK"
        )
        print("=" * 72)

        # ----------------------------------------------------
        # Benchmark each count
        # ----------------------------------------------------

        for sprite_count in BENCHMARK_SPRITE_COUNTS:

            sprites = generate_sprites(
                sprite_count,
                seed=1337,
            )

            result = run_benchmark(
                context,
                batch,
                texture,
                sprites,
                sprite_count,
            )

            if result is None:
                print()
                print(
                    "Benchmark cancelled."
                )
                return

            results.append(result)

            print(
                f"{sprite_count:>8,} sprites | "
                f"{result['fps']:>9.2f} FPS | "
                f"{result['frame_ms']:>8.3f} ms"
            )

        # ----------------------------------------------------
        # Results
        # ----------------------------------------------------

        print()
        print("=" * 72)
        print("RESULTS")
        print("=" * 72)

        print()

        print(
            f"{'Sprites':>12} | "
            f"{'FPS':>12} | "
            f"{'Frame ms':>12}"
        )

        print(
            "-" * 44
        )

        for result in results:
            print(
                f"{result['sprites']:>12,} | "
                f"{result['fps']:>12.2f} | "
                f"{result['frame_ms']:>12.3f}"
            )

        print()
        print("=" * 72)
        print("BENCHMARK COMPLETE")
        print("=" * 72)
        print()

    finally:
        print()
        print(
            "Shutting down..."
        )

        if batch is not None:
            try:
                batch.destroy()
            except Exception as exc:
                print(
                    f"Batch cleanup error: {exc}"
                )

        if texture is not None:
            try:
                texture.destroy()
            except Exception as exc:
                print(
                    f"Texture cleanup error: {exc}"
                )

        if context is not None:
            try:
                context.destroy()
            except Exception as exc:
                print(
                    f"Context cleanup error: {exc}"
                )

        try:
            pygame.quit()
        except Exception:
            pass

        print("Done.")


if __name__ == "__main__":
    main()