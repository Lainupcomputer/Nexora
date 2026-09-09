from __future__ import annotations

import random
import time
from dataclasses import dataclass

import pygame

from nexora import Engine


WIDTH = 1280
HEIGHT = 720

SPRITE_SIZE = 24

WARMUP_SECONDS = 1.0
MEASURE_SECONDS = 3.0

SPRITE_COUNTS = (
    100,
    500,
    1000,
    2500,
    5000,
    10000,
)


@dataclass(slots=True)
class BenchmarkCase:
    count: int
    rotating: bool
    batch: bool

    @property
    def name(self) -> str:
        mode = "rotating" if self.rotating else "static"
        renderer = "SpriteBatch" if self.batch else "Renderer.sprite"
        return f"{self.count} sprites - {mode} - {renderer}"


class RendererBenchmark:
    def __init__(self) -> None:
        self.engine = None
        self.renderer = None
        self.window = None
        self.input = None

        self.texture: pygame.Surface | None = None
        self.batch = None

        self.cases = []

        for count in SPRITE_COUNTS:
            for rotating in (False, True):
                for batch in (False, True):
                    self.cases.append(
                        BenchmarkCase(
                            count=count,
                            rotating=rotating,
                            batch=batch,
                        )
                    )

        self.case_index = -1
        self.current_case: BenchmarkCase | None = None

        self.positions: list[tuple[float, float]] = []
        self.rotations: list[float] = []

        self.mode = "idle"

        self.case_started_at = 0.0
        self.measure_started_at = 0.0

        self.frame_count = 0
        self.total_render_time = 0.0

        self.case_finished = False
        self.pending_next_case = False
        self.benchmark_finished = False

        self.results: list[dict] = []

    # =========================================================
    # Initialization
    # =========================================================

    def initialize(self) -> None:
        self.renderer = self.engine.renderer
        self.window = self.engine.window
        self.input = self.engine.input

        self.texture = self._create_texture()

        self.batch = self.renderer.create_sprite_batch(
            initial_capacity=1024,
            max_sprites=100_000,
            culling=False,
        )

        self._start_next_case()

    def _create_texture(self) -> pygame.Surface:
        surface = pygame.Surface(
            (SPRITE_SIZE, SPRITE_SIZE),
            pygame.SRCALPHA,
        )

        pygame.draw.rect(
            surface,
            (80, 180, 255),
            (1, 1, SPRITE_SIZE - 2, SPRITE_SIZE - 2),
            border_radius=4,
        )

        pygame.draw.rect(
            surface,
            (180, 230, 255),
            (4, 4, SPRITE_SIZE - 8, SPRITE_SIZE - 8),
            width=2,
            border_radius=3,
        )

        return surface

    # =========================================================
    # Case management
    # =========================================================

    def _start_next_case(self) -> None:
        self.case_index += 1

        if self.case_index >= len(self.cases):
            self._finish_benchmark()
            return

        self.current_case = self.cases[self.case_index]

        print()
        print("=" * 90)
        print(
            f"Case {self.case_index + 1}/{len(self.cases)}: "
            f"{self.current_case.name}"
        )
        print("=" * 90)

        self._generate_sprites(
            self.current_case.count
        )

        self.mode = "warmup"

        self.case_started_at = time.perf_counter()
        self.measure_started_at = 0.0

        self.frame_count = 0
        self.total_render_time = 0.0

        self.case_finished = False
        self.pending_next_case = False

        self.renderer.clear_sprite_cache()
        self.renderer.reset_sprite_cache_stats()

    def _generate_sprites(self, count: int) -> None:
        self.positions = []
        self.rotations = []

        random.seed(1337 + count)

        margin = SPRITE_SIZE

        for _ in range(count):
            self.positions.append(
                (
                    random.uniform(
                        margin,
                        WIDTH - margin,
                    ),
                    random.uniform(
                        margin,
                        HEIGHT - margin,
                    ),
                )
            )

            self.rotations.append(
                random.uniform(0.0, 360.0)
            )

    # =========================================================
    # Fixed update
    # =========================================================

    def fixed_update(self, delta_time: float) -> None:
        pass

    # =========================================================
    # Update
    # =========================================================

    def update(self, delta_time: float) -> None:
        if self.benchmark_finished:
            return

        if self.pending_next_case:
            self.pending_next_case = False
            self._start_next_case()
            return

        now = time.perf_counter()

        if self.mode == "warmup":
            if now - self.case_started_at >= WARMUP_SECONDS:
                self.mode = "measure"
                self.measure_started_at = now

                self.frame_count = 0
                self.total_render_time = 0.0

                self.renderer.clear_sprite_cache()
                self.renderer.reset_sprite_cache_stats()

                print("Measurement started...")

        elif self.mode == "measure":
            if now - self.measure_started_at >= MEASURE_SECONDS:
                self._finish_case()
                return

        if (
            self.current_case is not None
            and self.current_case.rotating
            and self.mode in ("warmup", "measure")
        ):
            rotation_delta = 90.0 * delta_time

            for index in range(len(self.rotations)):
                rotation = self.rotations[index] + rotation_delta

                if rotation >= 360.0:
                    rotation -= 360.0

                self.rotations[index] = rotation

    # =========================================================
    # Rendering
    # =========================================================

    def render(self) -> None:
        if self.renderer is None:
            return

        self.renderer.clear((18, 18, 24))

        if self.texture is None:
            return

        if self.current_case is None:
            return

        render_start = time.perf_counter()

        if self.current_case.batch:
            self._render_batch()
        else:
            self._render_direct()

        render_end = time.perf_counter()

        if self.mode == "measure":
            self.total_render_time += (
                render_end - render_start
            )
            self.frame_count += 1

        self._draw_overlay()

    # =========================================================
    # Direct renderer
    # =========================================================

    def _render_direct(self) -> None:
        assert self.texture is not None

        rotating = self.current_case.rotating

        for index, (x, y) in enumerate(self.positions):
            rotation = (
                self.rotations[index]
                if rotating
                else 0.0
            )

            self.renderer.sprite(
                self.texture,
                x,
                y,
                width=SPRITE_SIZE,
                height=SPRITE_SIZE,
                rotation=rotation,
            )

    # =========================================================
    # SpriteBatch
    # =========================================================

    def _render_batch(self) -> None:
        assert self.texture is not None
        assert self.batch is not None

        rotating = self.current_case.rotating

        self.batch.begin()

        for index, (x, y) in enumerate(self.positions):
            rotation = (
                self.rotations[index]
                if rotating
                else 0.0
            )

            self.batch.add_fast(
                self.texture,
                x,
                y,
                width=SPRITE_SIZE,
                height=SPRITE_SIZE,
                rotation=rotation,
            )

        self.batch.end()

    # =========================================================
    # Overlay
    # =========================================================

    def _draw_overlay(self) -> None:
        if self.benchmark_finished:
            self._draw_finished_overlay()
            return

        if self.current_case is None:
            return

        elapsed = 0.0

        if self.mode == "warmup":
            elapsed = (
                time.perf_counter()
                - self.case_started_at
            )

        elif self.mode == "measure":
            elapsed = (
                time.perf_counter()
                - self.measure_started_at
            )

        fps = 0.0
        render_ms = 0.0

        if self.frame_count > 0:
            if self.total_render_time > 0:
                render_ms = (
                    self.total_render_time
                    / self.frame_count
                    * 1000.0
                )

                fps = (
                    self.frame_count
                    / self.total_render_time
                )

        hit_rate = self.renderer.sprite_cache_hit_rate

        renderer_name = (
            "SpriteBatch"
            if self.current_case.batch
            else "Renderer.sprite"
        )

        lines = [
            "NEXORA SPRITE BATCH BENCHMARK",
            "",
            f"Case: {self.case_index + 1}/{len(self.cases)}",
            f"Sprites: {self.current_case.count:,}",
            f"Renderer: {renderer_name}",
            f"Mode: {'ROTATING' if self.current_case.rotating else 'STATIC'}",
            f"Phase: {self.mode.upper()}",
            "",
            f"Time: {elapsed:.2f}s",
            f"FPS: {fps:,.1f}",
            f"Render: {render_ms:.3f} ms",
            "",
            f"Cache: {self.renderer.sprite_cache_size:,}",
            f"Hits: {self.renderer.sprite_cache_hits:,}",
            f"Misses: {self.renderer.sprite_cache_misses:,}",
            f"Hit rate: {hit_rate * 100.0:.2f}%",
            "",
            "ESC = abort",
        ]

        if self.current_case.batch and self.batch is not None:
            lines.extend(
                [
                    "",
                    f"Batch submitted: {self.batch.submitted:,}",
                    f"Batch rendered: {self.batch.rendered:,}",
                    f"Batch culled: {self.batch.culled:,}",
                    f"Batch flushes: {self.batch.flushes:,}",
                ]
            )

        y = 12

        for line in lines:
            self.renderer.text(
                line,
                12,
                y,
                color=(235, 235, 240),
                size=20,
            )

            y += 23

    def _draw_finished_overlay(self) -> None:
        lines = [
            "NEXORA SPRITE BATCH BENCHMARK",
            "",
            "BENCHMARK COMPLETE",
            "",
            "Results printed to terminal.",
            "",
            "ESC = close",
        ]

        y = 40

        for line in lines:
            self.renderer.text(
                line,
                40,
                y,
                color=(235, 235, 240),
                size=28,
            )

            y += 36

    # =========================================================
    # Finish case
    # =========================================================

    def _finish_case(self) -> None:
        if self.case_finished:
            return

        self.case_finished = True
        self.mode = "done"

        assert self.current_case is not None

        elapsed = max(
            time.perf_counter()
            - self.measure_started_at,
            0.000001,
        )

        fps = self.frame_count / elapsed

        render_ms = (
            self.total_render_time
            / max(self.frame_count, 1)
            * 1000.0
        )

        result = {
            "sprites": self.current_case.count,
            "rotating": self.current_case.rotating,
            "batch": self.current_case.batch,
            "frames": self.frame_count,
            "fps": fps,
            "render_ms": render_ms,
            "cache_size": self.renderer.sprite_cache_size,
            "cache_hits": self.renderer.sprite_cache_hits,
            "cache_misses": self.renderer.sprite_cache_misses,
            "cache_hit_rate": self.renderer.sprite_cache_hit_rate,
        }

        self.results.append(result)

        renderer_name = (
            "SpriteBatch"
            if result["batch"]
            else "Renderer.sprite"
        )

        mode_name = (
            "rotating"
            if result["rotating"]
            else "static"
        )

        print(
            f"Sprites:      {result['sprites']:,}"
        )
        print(
            f"Renderer:     {renderer_name}"
        )
        print(
            f"Mode:         {mode_name}"
        )
        print(
            f"Frames:       {result['frames']:,}"
        )
        print(
            f"FPS:          {result['fps']:,.2f}"
        )
        print(
            f"Render time:  {result['render_ms']:.3f} ms"
        )
        print(
            f"Cache size:   {result['cache_size']:,}"
        )
        print(
            f"Cache hits:   {result['cache_hits']:,}"
        )
        print(
            f"Cache misses: {result['cache_misses']:,}"
        )
        print(
            f"Cache hit:    "
            f"{result['cache_hit_rate'] * 100.0:.2f}%"
        )

        if result["batch"]:
            print(
                f"Batch rendered: "
                f"{self.batch.rendered:,}"
            )

        print()
        print("Case finished.")

        self.pending_next_case = True

    # =========================================================
    # Final results
    # =========================================================

    def _finish_benchmark(self) -> None:
        if self.benchmark_finished:
            return

        self.benchmark_finished = True
        self.mode = "finished"

        print()
        print()
        print("=" * 115)
        print("NEXORA SPRITE BATCH BENCHMARK RESULTS")
        print("=" * 115)

        print(
            f"{'Sprites':>8} "
            f"{'Renderer':>16} "
            f"{'Mode':>10} "
            f"{'FPS':>10} "
            f"{'Render ms':>12} "
            f"{'Cache':>8} "
            f"{'Hit %':>10}"
        )

        print("-" * 115)

        for result in self.results:
            renderer_name = (
                "SpriteBatch"
                if result["batch"]
                else "Renderer.sprite"
            )

            mode_name = (
                "rotating"
                if result["rotating"]
                else "static"
            )

            print(
                f"{result['sprites']:>8,} "
                f"{renderer_name:>16} "
                f"{mode_name:>10} "
                f"{result['fps']:>10.2f} "
                f"{result['render_ms']:>12.3f} "
                f"{result['cache_size']:>8,} "
                f"{result['cache_hit_rate'] * 100:>9.2f}%"
            )

        print("=" * 115)

        self._print_comparison()

        print()
        print("Benchmark complete.")
        print("Press ESC or close the window.")

    # =========================================================
    # Comparison
    # =========================================================

    def _print_comparison(self) -> None:
        print()
        print("=" * 115)
        print("SPRITEBATCH SPEEDUP")
        print("=" * 115)

        print(
            f"{'Sprites':>8} "
            f"{'Mode':>10} "
            f"{'Direct ms':>12} "
            f"{'Batch ms':>12} "
            f"{'Speedup':>12}"
        )

        print("-" * 115)

        for count in SPRITE_COUNTS:
            for rotating in (False, True):
                direct = next(
                    (
                        r
                        for r in self.results
                        if r["sprites"] == count
                        and r["rotating"] == rotating
                        and not r["batch"]
                    ),
                    None,
                )

                batch = next(
                    (
                        r
                        for r in self.results
                        if r["sprites"] == count
                        and r["rotating"] == rotating
                        and r["batch"]
                    ),
                    None,
                )

                if direct is None or batch is None:
                    continue

                direct_ms = direct["render_ms"]
                batch_ms = batch["render_ms"]

                speedup = (
                    direct_ms / batch_ms
                    if batch_ms > 0
                    else 0.0
                )

                mode_name = (
                    "rotating"
                    if rotating
                    else "static"
                )

                print(
                    f"{count:>8,} "
                    f"{mode_name:>10} "
                    f"{direct_ms:>12.3f} "
                    f"{batch_ms:>12.3f} "
                    f"{speedup:>11.2f}x"
                )

        print("=" * 115)

    # =========================================================
    # Events
    # =========================================================

    def handle_event(
        self,
        event: pygame.event.Event,
    ) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.engine.stop()

    # =========================================================
    # Shutdown
    # =========================================================

    def shutdown(self) -> None:
        pass


def main() -> None:
    game = RendererBenchmark()

    engine = Engine(
        game,
        width=WIDTH,
        height=HEIGHT,
        title="Nexora SpriteBatch Benchmark",
        target_fps=0,
        vsync=False,
        resizable=False,
    )

    engine.run()


if __name__ == "__main__":
    main()
