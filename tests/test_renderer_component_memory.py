from __future__ import annotations

import gc
import os
from importlib.util import (
    module_from_spec,
    spec_from_file_location,
)
from pathlib import Path

import psutil
import pytest

from nexora.core.engine import Engine

from nexora.rendering.gpu.shape_batch import (
    GPUShapeBatch,
)
from nexora.rendering.gpu.text_renderer import (
    GPUTextRenderer,
)


# ==============================================================
# PATHS
# ==============================================================

ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "camera"
    / "cinematic_camera_2d.py"
)


# ==============================================================
# MEMORY HELPERS
# ==============================================================


def _mb(
    value: int | float,
) -> float:
    return (
        float(value)
        / (1024.0 ** 2)
    )


def _rss_mb(
    process: psutil.Process,
) -> float:
    gc.collect()

    return _mb(
        process.memory_info().rss
    )


def _print_table(
    title: str,
    measurements: list[
        tuple[
            str,
            float,
            float,
        ]
    ],
) -> None:
    print()
    print("=" * 96)
    print(f" {title}")
    print("=" * 96)
    print()

    print(
        f"{'Step':<42}"
        f"{'Before':>14}"
        f"{'After':>14}"
        f"{'Delta':>14}"
    )

    print("-" * 96)

    for (
        name,
        before,
        after,
    ) in measurements:
        print(
            f"{name:<42}"
            f"{before:>11.1f} MB"
            f"{after:>11.1f} MB"
            f"{after - before:>+11.1f} MB"
        )

    print("-" * 96)

    total = sum(
        after - before
        for (
            _,
            before,
            after,
        ) in measurements
    )

    print(
        f"{'MEASURED TOTAL':<42}"
        f"{'':>14}"
        f"{'':>14}"
        f"{total:>+11.1f} MB"
    )

    print()


# ==============================================================
# EXAMPLE LOADER
# ==============================================================


def _load_example_class():
    if not EXAMPLE_PATH.is_file():
        raise FileNotFoundError(
            f"Example not found: {EXAMPLE_PATH}"
        )

    spec = spec_from_file_location(
        "nexora_renderer_memory_example",
        EXAMPLE_PATH,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"Could not load example: "
            f"{EXAMPLE_PATH}"
        )

    module = module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    example_class = getattr(
        module,
        "CinematicCameraExample",
        None,
    )

    if example_class is None:
        raise RuntimeError(
            "CinematicCameraExample not found"
        )

    return example_class


# ==============================================================
# METHOD INSTRUMENTATION
# ==============================================================


def _instrument_method(
    monkeypatch,
    cls,
    method_name: str,
    measurements: list[
        tuple[
            str,
            float,
            float,
        ]
    ],
    process: psutil.Process,
    label: str | None = None,
) -> bool:
    original = getattr(
        cls,
        method_name,
        None,
    )

    if original is None:
        return False

    if not callable(
        original
    ):
        return False

    name = (
        label
        if label is not None
        else (
            f"{cls.__name__}."
            f"{method_name}"
        )
    )

    def wrapped(
        self,
        *args,
        **kwargs,
    ):
        before = _rss_mb(
            process
        )

        result = original(
            self,
            *args,
            **kwargs,
        )

        after = _rss_mb(
            process
        )

        measurements.append(
            (
                name,
                before,
                after,
            )
        )

        return result

    monkeypatch.setattr(
        cls,
        method_name,
        wrapped,
    )

    return True


# ==============================================================
# TEST
# ==============================================================


@pytest.mark.gpu
@pytest.mark.slow
def test_renderer_component_memory(
    monkeypatch,
) -> None:
    """
    Profile GPUShapeBatch and GPUTextRenderer initialization
    internally.

    This reveals which exact resource creation call causes the
    large native RSS jump.
    """

    process = psutil.Process(
        os.getpid()
    )

    baseline = _rss_mb(
        process
    )

    print()
    print("=" * 96)
    print(" Nexora Renderer Component Memory Profiler")
    print("=" * 96)
    print()
    print(
        f"Baseline RSS: "
        f"{baseline:.1f} MB"
    )
    print()

    # ==========================================================
    # RESULTS
    # ==============================================================

    shape_measurements: list[
        tuple[
            str,
            float,
            float,
        ]
    ] = []

    text_measurements: list[
        tuple[
            str,
            float,
            float,
        ]
    ] = []

    # ==========================================================
    # SHAPE BATCH
    # ==============================================================

    shape_methods = [
        "_create_shaders",
        "_create_quad",
        "_create_instance_buffer",
        "_create_buffers",
        "_create_pipeline",
        "_create_fill_pipeline",
        "_create_geometry_pipeline",
        "_create_outline_pipeline",
        "_create_shape_pipeline",
        "_create_geometry_resources",
        "_create_resources",
    ]

    print(
        "Instrumenting GPUShapeBatch:"
    )

    for method_name in shape_methods:
        found = _instrument_method(
            monkeypatch,
            GPUShapeBatch,
            method_name,
            shape_measurements,
            process,
        )

        if found:
            print(
                f"  + {method_name}"
            )

    print()

    # ==========================================================
    # TEXT RENDERER
    # ==============================================================

    text_methods = [
        "_create_quad_buffer",
        "_create_instance_buffer",
        "_create_pipeline",
        "_create_resources",
    ]

    print(
        "Instrumenting GPUTextRenderer:"
    )

    for method_name in text_methods:
        found = _instrument_method(
            monkeypatch,
            GPUTextRenderer,
            method_name,
            text_measurements,
            process,
        )

        if found:
            print(
                f"  + {method_name}"
            )

    print()

    # ==========================================================
    # TEXT ATLAS CONSTRUCTION
    # ==========================================================
    #
    # The atlas is created directly through:
    #
    #     self.atlas = GPUFontAtlas(...)
    #
    # so we instrument its constructor separately.
    # ==============================================================

    try:
        from nexora.rendering.gpu.font_atlas import (
            GPUFontAtlas,
        )

    except ImportError:
        GPUFontAtlas = None

    if GPUFontAtlas is not None:
        original_atlas_init = (
            GPUFontAtlas.__init__
        )

        def atlas_init(
            self,
            *args,
            **kwargs,
        ):
            before = _rss_mb(
                process
            )

            original_atlas_init(
                self,
                *args,
                **kwargs,
            )

            after = _rss_mb(
                process
            )

            text_measurements.append(
                (
                    "GPUFontAtlas.__init__",
                    before,
                    after,
                )
            )

        monkeypatch.setattr(
            GPUFontAtlas,
            "__init__",
            atlas_init,
        )

        print(
            "  + GPUFontAtlas.__init__"
        )

    # ==========================================================
    # GPU BUFFER CREATION
    # ==============================================================

    try:
        from nexora.rendering.gpu.buffer import (
            GPUBuffer,
        )

    except ImportError:
        GPUBuffer = None

    buffer_measurements: list[
        tuple[
            str,
            float,
            float,
        ]
    ] = []

    if GPUBuffer is not None:
        original_gpu_buffer_create = (
            GPUBuffer._create_gpu_buffer
        )

        def gpu_buffer_create(
            self,
        ):
            before = _rss_mb(
                process
            )

            result = (
                original_gpu_buffer_create(
                    self
                )
            )

            after = _rss_mb(
                process
            )

            buffer_measurements.append(
                (
                    (
                        "GPUBuffer "
                        f"{self.size / (1024 ** 2):.2f} MB"
                    ),
                    before,
                    after,
                )
            )

            return result

        monkeypatch.setattr(
            GPUBuffer,
            "_create_gpu_buffer",
            gpu_buffer_create,
        )

        original_transfer_create = (
            GPUBuffer._create_transfer_buffer
        )

        def transfer_create(
            self,
        ):
            before = _rss_mb(
                process
            )

            result = (
                original_transfer_create(
                    self
                )
            )

            after = _rss_mb(
                process
            )

            buffer_measurements.append(
                (
                    (
                        "TransferBuffer "
                        f"{self.size / (1024 ** 2):.2f} MB"
                    ),
                    before,
                    after,
                )
            )

            return result

        monkeypatch.setattr(
            GPUBuffer,
            "_create_transfer_buffer",
            transfer_create,
        )

    # ==========================================================
    # ENGINE.RUN INTERCEPT
    # ==============================================================

    engine_run_reached = False

    def intercepted_engine_run(
        self,
    ) -> None:
        nonlocal engine_run_reached

        engine_run_reached = True

        # Do not enter the actual GameLoop.

    monkeypatch.setattr(
        Engine,
        "run",
        intercepted_engine_run,
    )

    # ==========================================================
    # RUN NORMAL STARTUP
    # ==============================================================

    CinematicCameraExample = (
        _load_example_class()
    )

    game = (
        CinematicCameraExample()
    )

    before_run = _rss_mb(
        process
    )

    game.run()

    after_run = _rss_mb(
        process
    )

    assert engine_run_reached

    # ==========================================================
    # RESULTS
    # ==============================================================

    print()
    print(
        f"Before Game.run(): "
        f"{before_run:.1f} MB"
    )

    print(
        f"After Game.run():  "
        f"{after_run:.1f} MB"
    )

    print(
        f"Startup delta:      "
        f"{after_run - before_run:+.1f} MB"
    )

    # ----------------------------------------------------------
    # Shape
    # ----------------------------------------------------------

    _print_table(
        "GPUShapeBatch Internal Memory",
        shape_measurements,
    )

    # ----------------------------------------------------------
    # Text
    # ----------------------------------------------------------

    _print_table(
        "GPUTextRenderer Internal Memory",
        text_measurements,
    )

    # ----------------------------------------------------------
    # Buffers
    # ----------------------------------------------------------

    if buffer_measurements:
        _print_table(
            "GPUBuffer / TransferBuffer Memory",
            buffer_measurements,
        )

    # ==========================================================
    # LARGEST MEASUREMENTS
    # ==============================================================

    all_measurements = (
        shape_measurements
        + text_measurements
        + buffer_measurements
    )

    if all_measurements:
        ranked = sorted(
            all_measurements,
            key=lambda item: (
                item[2]
                - item[1]
            ),
            reverse=True,
        )

        print()
        print("=" * 96)
        print(
            " Largest Individual Memory Jumps"
        )
        print("=" * 96)
        print()

        for (
            name,
            before,
            after,
        ) in ranked[:15]:
            print(
                f"{name:<52}"
                f"{after - before:>+10.1f} MB"
            )

        print()

    # Diagnostic test.
    assert True