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

from nexora.rendering.gpu.sprite_batch import (
    GPUSpriteBatch,
)
from nexora.rendering.gpu.rect_batch import (
    GPURectBatch,
)
from nexora.rendering.gpu.line_batch import (
    GPULineBatch,
)
from nexora.rendering.gpu.shape_batch import (
    GPUShapeBatch,
)
from nexora.rendering.gpu.text_renderer import (
    GPUTextRenderer,
)
from nexora.rendering.postprocessing.post_process import (
    PostProcess,
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
# MEMORY
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
    """
    Return process RSS.

    GC is deliberately triggered so short-lived Python garbage
    does not distort constructor measurements too much.
    """

    gc.collect()

    return _mb(
        process.memory_info().rss
    )


# ==============================================================
# EXAMPLE LOADING
# ==============================================================


def _load_example_class():
    if not EXAMPLE_PATH.is_file():
        raise FileNotFoundError(
            f"Example not found: "
            f"{EXAMPLE_PATH}"
        )

    spec = spec_from_file_location(
        "nexora_startup_memory_example",
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
            "CinematicCameraExample "
            "was not found in "
            f"{EXAMPLE_PATH}"
        )

    return example_class


# ==============================================================
# OUTPUT
# ==============================================================


def _print_measurement_table(
    measurements: list[
        tuple[
            str,
            float,
            float,
        ]
    ],
) -> None:
    print()

    print(
        "=" * 86
    )

    print(
        " Nexora Renderer Startup Memory Breakdown"
    )

    print(
        "=" * 86
    )

    print()

    print(
        f"{'Component':<34}"
        f"{'Before':>12}"
        f"{'After':>12}"
        f"{'Delta':>12}"
    )

    print(
        "-" * 86
    )

    for (
        name,
        before,
        after,
    ) in measurements:
        delta = (
            after
            - before
        )

        print(
            f"{name:<34}"
            f"{before:>9.1f} MB"
            f"{after:>9.1f} MB"
            f"{delta:>+9.1f} MB"
        )

    print(
        "-" * 86
    )


# ==============================================================
# TEST
# ==============================================================


@pytest.mark.gpu
@pytest.mark.slow
def test_startup_memory_breakdown(
    monkeypatch,
) -> None:
    """
    Measure native process RSS while Nexora's renderer subsystems
    are constructed.

    This intentionally uses the normal Game.run() startup path.

    Engine.run() itself is intercepted so the actual infinite
    GameLoop does not start.
    """

    process = psutil.Process(
        os.getpid()
    )

    measurements: list[
        tuple[
            str,
            float,
            float,
        ]
    ] = []

    startup_points: list[
        tuple[
            str,
            float,
        ]
    ] = []

    # ==========================================================
    # BASELINE
    # ==============================================================

    baseline = _rss_mb(
        process
    )

    print()

    print(
        "=" * 86
    )

    print(
        " Nexora Startup Memory Profiler"
    )

    print(
        "=" * 86
    )

    print()

    print(
        f"Baseline: "
        f"{baseline:.1f} MB"
    )

    print()

    # ==========================================================
    # CONSTRUCTOR WRAPPER
    # ==============================================================

    def instrument_constructor(
        cls,
        name: str,
    ) -> None:
        original_init = (
            cls.__init__
        )

        def wrapped_init(
            self,
            *args,
            **kwargs,
        ):
            before = _rss_mb(
                process
            )

            original_init(
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

        monkeypatch.setattr(
            cls,
            "__init__",
            wrapped_init,
        )

    # ==========================================================
    # INSTRUMENT RENDERER COMPONENTS
    # ==============================================================

    instrument_constructor(
        GPUSpriteBatch,
        "GPUSpriteBatch",
    )

    instrument_constructor(
        GPURectBatch,
        "GPURectBatch",
    )

    instrument_constructor(
        GPULineBatch,
        "GPULineBatch",
    )

    instrument_constructor(
        GPUShapeBatch,
        "GPUShapeBatch",
    )

    instrument_constructor(
        GPUTextRenderer,
        "GPUTextRenderer",
    )

    instrument_constructor(
        PostProcess,
        "PostProcess",
    )

    # ==========================================================
    # ENGINE SERVICE TRACKING
    # ==============================================================

    original_engine_setattr = (
        Engine.__setattr__
    )

    interesting_services = {
        "assets": "Assets",
        "gpu_context": "GPUContext",
        "renderer": "Renderer complete",
        "input": "Input",
        "audio": "Audio",
        "loop": "GameLoop",
        "debug_overlay": "DebugOverlay",
    }

    seen_services: set[str] = set()

    def tracked_engine_setattr(
        self,
        name,
        value,
    ):
        original_engine_setattr(
            self,
            name,
            value,
        )

        if (
            name not in interesting_services
            or name in seen_services
            or value is None
        ):
            return

        seen_services.add(
            name
        )

        startup_points.append(
            (
                interesting_services[
                    name
                ],
                _rss_mb(
                    process
                ),
            )
        )

    monkeypatch.setattr(
        Engine,
        "__setattr__",
        tracked_engine_setattr,
    )

    # ==========================================================
    # INTERCEPT ENGINE.RUN
    # ==============================================================

    engine_run_reached = False

    def intercepted_engine_run(
        self,
    ) -> None:
        nonlocal engine_run_reached

        engine_run_reached = True

        startup_points.append(
            (
                "Before GameLoop.run",
                _rss_mb(
                    process
                ),
            )
        )

        # Intentionally do not start self.loop.run().

    monkeypatch.setattr(
        Engine,
        "run",
        intercepted_engine_run,
    )

    # ==========================================================
    # LOAD EXAMPLE
    # ==============================================================

    CinematicCameraExample = (
        _load_example_class()
    )

    after_import = _rss_mb(
        process
    )

    startup_points.append(
        (
            "Example imported",
            after_import,
        )
    )

    # ==========================================================
    # GAME OBJECT
    # ==============================================================

    game = (
        CinematicCameraExample()
    )

    after_game = _rss_mb(
        process
    )

    startup_points.append(
        (
            "Game constructed",
            after_game,
        )
    )

    # ==========================================================
    # NORMAL STARTUP
    # ==============================================================

    game.run()

    assert engine_run_reached, (
        "Engine.run() was not reached."
    )

    # ==========================================================
    # RENDERER COMPONENT RESULTS
    # ==============================================================

    _print_measurement_table(
        measurements
    )

    # ==========================================================
    # SUM COMPONENT GROWTH
    # ==============================================================

    measured_total = sum(
        after - before
        for (
            _,
            before,
            after,
        ) in measurements
    )

    print()

    print(
        f"Measured renderer component growth: "
        f"{measured_total:.1f} MB"
    )

    print()

    # ==========================================================
    # ENGINE STARTUP TABLE
    # ==============================================================

    print(
        "=" * 86
    )

    print(
        " Engine Startup Stages"
    )

    print(
        "=" * 86
    )

    print()

    print(
        f"{'Stage':<34}"
        f"{'RSS':>12}"
        f"{'Delta':>12}"
        f"{'Total':>12}"
    )

    print(
        "-" * 86
    )

    previous = baseline

    for (
        name,
        value,
    ) in startup_points:
        delta = (
            value
            - previous
        )

        total = (
            value
            - baseline
        )

        print(
            f"{name:<34}"
            f"{value:>9.1f} MB"
            f"{delta:>+9.1f} MB"
            f"{total:>+9.1f} MB"
        )

        previous = value

    print(
        "-" * 86
    )

    # ==========================================================
    # LARGEST COMPONENT
    # ==============================================================

    if measurements:
        largest = max(
            measurements,
            key=lambda item: (
                item[2]
                - item[1]
            ),
        )

        (
            largest_name,
            largest_before,
            largest_after,
        ) = largest

        largest_delta = (
            largest_after
            - largest_before
        )

        print()

        print(
            "Largest renderer allocation:"
        )

        print(
            f"  {largest_name}: "
            f"{largest_delta:.1f} MB"
        )

        print()

    # ==========================================================
    # DIAGNOSTIC TEST
    # ==============================================================

    assert measurements, (
        "No renderer component constructors "
        "were measured."
    )