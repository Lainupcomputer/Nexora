from __future__ import annotations

import gc
import os
import threading
import time
import tracemalloc
from importlib.util import (
    module_from_spec,
    spec_from_file_location,
)
from pathlib import Path

import psutil
import pytest


# ==============================================================
# CONFIG
# ==============================================================

TEST_DURATION_SECONDS = 60.0
SAMPLE_INTERVAL_SECONDS = 5.0

# Ignore the first samples because SDL, Vulkan, shaders and Python
# can still allocate startup caches.
WARMUP_SAMPLES = 3

# Allowed growth after warmup.
MAX_RSS_GROWTH_MB = 40.0
MAX_PYTHON_GROWTH_MB = 15.0

# Continuous growth above this is suspicious even when the total
# threshold was not reached yet.
MAX_RSS_SLOPE_MB_PER_SECOND = 0.40
MAX_PYTHON_SLOPE_MB_PER_SECOND = 0.15


# ==============================================================
# PATHS
# ==============================================================

ROOT = Path(__file__).resolve().parent.parent

EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "camera"
    / "cinematic_camera_2d.py"
)


# ==============================================================
# HELPERS
# ==============================================================


def _to_mb(
    value: int | float,
) -> float:
    return (
        float(value)
        / (1024.0 ** 2)
    )


def _linear_slope(
    values: list[float],
    sample_interval: float,
) -> float:
    """
    Return the linear growth rate in MB/s.
    """

    count = len(
        values
    )

    if count < 2:
        return 0.0

    xs = [
        index * sample_interval
        for index in range(
            count
        )
    ]

    x_mean = (
        sum(xs)
        / count
    )

    y_mean = (
        sum(values)
        / count
    )

    numerator = sum(
        (
            x - x_mean
        )
        * (
            y - y_mean
        )
        for x, y in zip(
            xs,
            values,
        )
    )

    denominator = sum(
        (
            x - x_mean
        ) ** 2
        for x in xs
    )

    if denominator == 0.0:
        return 0.0

    return (
        numerator
        / denominator
    )


def _load_example_class():
    """
    Load CinematicCameraExample directly from its example file.

    The examples directory does not need to be a Python package.
    """

    if not EXAMPLE_PATH.is_file():
        raise FileNotFoundError(
            f"Example not found: {EXAMPLE_PATH}"
        )

    spec = spec_from_file_location(
        "nexora_memory_test_example",
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
            "CinematicCameraExample was not found in "
            f"{EXAMPLE_PATH}"
        )

    return example_class


# ==============================================================
# TEST
# ==============================================================


@pytest.mark.gpu
@pytest.mark.slow
def test_idle_memory_does_not_leak() -> None:
    """
    Run the real CinematicCameraExample through Game.run() and
    monitor memory while the example sits idle.

    Interpretation:

        RSS grows + Python heap grows
            -> likely Python-side leak

        RSS grows + Python heap stays stable
            -> likely native SDL / Vulkan / ctypes leak

        Both remain stable
            -> no obvious idle leak
    """

    process = psutil.Process(
        os.getpid()
    )

    # ----------------------------------------------------------
    # Python allocation tracing
    # ----------------------------------------------------------

    tracemalloc.start(
        25
    )

    gc.collect()

    # ----------------------------------------------------------
    # Example
    # ----------------------------------------------------------

    CinematicCameraExample = (
        _load_example_class()
    )

    game = (
        CinematicCameraExample()
    )

    # ----------------------------------------------------------
    # Results
    # ----------------------------------------------------------

    rss_samples: list[float] = []
    python_samples: list[float] = []
    python_peak_samples: list[float] = []

    sample_times: list[float] = []

    monitor_errors: list[
        BaseException
    ] = []

    stop_monitor = (
        threading.Event()
    )

    game_finished = (
        threading.Event()
    )

    start_time = (
        time.perf_counter()
    )

    print()
    print("=" * 72)
    print(" Nexora Idle Memory Leak Test")
    print("=" * 72)
    print()
    print(
        f"Example: {EXAMPLE_PATH}"
    )
    print(
        f"Duration: "
        f"{TEST_DURATION_SECONDS:.0f}s"
    )
    print(
        f"Sample interval: "
        f"{SAMPLE_INTERVAL_SECONDS:.1f}s"
    )
    print()
    print(
        "The example is running through the normal Game.run() path."
    )
    print()

    # ==========================================================
    # MONITOR THREAD
    # ==============================================================

    def memory_monitor() -> None:
        try:
            next_sample = (
                time.perf_counter()
            )

            while not stop_monitor.is_set():
                now = (
                    time.perf_counter()
                )

                elapsed = (
                    now
                    - start_time
                )

                # --------------------------------------------------
                # Stop game after requested duration
                # --------------------------------------------------

                if (
                    elapsed
                    >= TEST_DURATION_SECONDS
                ):
                    print()
                    print(
                        "Test duration reached - stopping game..."
                    )

                    try:
                        game.stop()

                    except Exception as exc:
                        monitor_errors.append(
                            exc
                        )

                    return

                # --------------------------------------------------
                # Sample
                # --------------------------------------------------

                if now >= next_sample:
                    rss_mb = _to_mb(
                        process.memory_info().rss
                    )

                    (
                        traced_current,
                        traced_peak,
                    ) = (
                        tracemalloc.get_traced_memory()
                    )

                    python_mb = _to_mb(
                        traced_current
                    )

                    python_peak_mb = _to_mb(
                        traced_peak
                    )

                    rss_samples.append(
                        rss_mb
                    )

                    python_samples.append(
                        python_mb
                    )

                    python_peak_samples.append(
                        python_peak_mb
                    )

                    sample_times.append(
                        elapsed
                    )

                    print(
                        f"{elapsed:6.1f}s"
                        f" | RSS: "
                        f"{rss_mb:8.1f} MB"
                        f" | Python: "
                        f"{python_mb:7.1f} MB"
                        f" | Py Peak: "
                        f"{python_peak_mb:7.1f} MB"
                    )

                    next_sample += (
                        SAMPLE_INTERVAL_SECONDS
                    )

                # --------------------------------------------------
                # Do not busy-loop.
                # --------------------------------------------------

                stop_monitor.wait(
                    0.05
                )

        except BaseException as exc:
            monitor_errors.append(
                exc
            )

            try:
                game.stop()

            except Exception:
                pass

    monitor_thread = threading.Thread(
        target=memory_monitor,
        name="nexora-memory-monitor",
        daemon=True,
    )

    monitor_thread.start()

    # ==========================================================
    # NORMAL NEXORA RUN
    # ==============================================================

    run_error: BaseException | None = None

    try:
        # ------------------------------------------------------
        # IMPORTANT
        #
        # This is the normal Nexora lifecycle.
        #
        # Game.run() creates/initializes the Engine and starts the
        # actual GameLoop. We deliberately do NOT manually call
        # engine.initialize().
        # ------------------------------------------------------

        game.run()

    except BaseException as exc:
        run_error = exc

    finally:
        game_finished.set()

        stop_monitor.set()

        monitor_thread.join(
            timeout=5.0
        )

    # ==========================================================
    # FAIL ON RUNTIME ERROR
    # ==============================================================

    if run_error is not None:
        raise run_error

    if monitor_errors:
        raise monitor_errors[0]

    # ==========================================================
    # VALIDATE SAMPLES
    # ==============================================================

    print()
    print("=" * 72)
    print(" Memory Analysis")
    print("=" * 72)
    print()

    if (
        len(rss_samples)
        <= WARMUP_SAMPLES + 1
    ):
        pytest.fail(
            "Not enough memory samples collected. "
            f"Collected only {len(rss_samples)} samples."
        )

    # ----------------------------------------------------------
    # Ignore startup/warmup
    # ----------------------------------------------------------

    rss_analysis = (
        rss_samples[
            WARMUP_SAMPLES:
        ]
    )

    python_analysis = (
        python_samples[
            WARMUP_SAMPLES:
        ]
    )

    # ==========================================================
    # GROWTH
    # ==============================================================

    rss_start = (
        rss_analysis[0]
    )

    rss_end = (
        rss_analysis[-1]
    )

    rss_growth = (
        rss_end
        - rss_start
    )

    python_start = (
        python_analysis[0]
    )

    python_end = (
        python_analysis[-1]
    )

    python_growth = (
        python_end
        - python_start
    )

    # ==========================================================
    # SLOPE
    # ==============================================================

    rss_slope = (
        _linear_slope(
            rss_analysis,
            SAMPLE_INTERVAL_SECONDS,
        )
    )

    python_slope = (
        _linear_slope(
            python_analysis,
            SAMPLE_INTERVAL_SECONDS,
        )
    )

    # ==========================================================
    # OUTPUT
    # ==============================================================

    print(
        f"Samples total:       "
        f"{len(rss_samples)}"
    )

    print(
        f"Samples analyzed:    "
        f"{len(rss_analysis)}"
    )

    print()

    print(
        f"RSS start:           "
        f"{rss_start:.1f} MB"
    )

    print(
        f"RSS end:             "
        f"{rss_end:.1f} MB"
    )

    print(
        f"RSS growth:          "
        f"{rss_growth:+.1f} MB"
    )

    print(
        f"RSS slope:           "
        f"{rss_slope:+.3f} MB/s"
    )

    print()

    print(
        f"Python start:        "
        f"{python_start:.1f} MB"
    )

    print(
        f"Python end:          "
        f"{python_end:.1f} MB"
    )

    print(
        f"Python growth:       "
        f"{python_growth:+.1f} MB"
    )

    print(
        f"Python slope:        "
        f"{python_slope:+.3f} MB/s"
    )

    print()

    # ==========================================================
    # DIAGNOSIS
    # ==============================================================

    native_growth = (
        rss_growth
        > MAX_RSS_GROWTH_MB
        or rss_slope
        > MAX_RSS_SLOPE_MB_PER_SECOND
    )

    python_growth_detected = (
        python_growth
        > MAX_PYTHON_GROWTH_MB
        or python_slope
        > MAX_PYTHON_SLOPE_MB_PER_SECOND
    )

    if (
        native_growth
        and not python_growth_detected
    ):
        print(
            "Diagnosis:"
        )

        print(
            "  RSS is continuously growing, but the Python heap "
            "is comparatively stable."
        )

        print(
            "  This strongly points to native memory:"
        )

        print(
            "    SDL_GPU / Vulkan / ctypes / driver allocations."
        )

    elif python_growth_detected:
        print(
            "Diagnosis:"
        )

        print(
            "  Python traced memory is continuously growing."
        )

        print(
            "  This points to retained Python objects / containers."
        )

    else:
        print(
            "Diagnosis:"
        )

        print(
            "  No strong continuous idle memory leak was detected."
        )

    print()

    # ==========================================================
    # ASSERTIONS
    # ==============================================================

    assert (
        rss_growth
        <= MAX_RSS_GROWTH_MB
    ), (
        "Possible native/GPU memory leak: "
        f"RSS increased by {rss_growth:.1f} MB "
        f"after warmup."
    )

    assert (
        rss_slope
        <= MAX_RSS_SLOPE_MB_PER_SECOND
    ), (
        "Possible continuous native/GPU memory leak: "
        f"RSS is growing at {rss_slope:.3f} MB/s."
    )

    assert (
        python_growth
        <= MAX_PYTHON_GROWTH_MB
    ), (
        "Possible Python memory leak: "
        f"traced heap increased by "
        f"{python_growth:.1f} MB."
    )

    assert (
        python_slope
        <= MAX_PYTHON_SLOPE_MB_PER_SECOND
    ), (
        "Possible continuous Python memory leak: "
        f"Python heap is growing at "
        f"{python_slope:.3f} MB/s."
    )