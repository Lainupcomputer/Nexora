from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import psutil


# ==============================================================
# CONFIG
# ==============================================================

ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

EXAMPLE = (
    ROOT
    / "examples"
    / "debug"
        / "game_loop_memory_test.py"
)

DURATION_SECONDS = 30.0
SAMPLE_INTERVAL = 2.0


# ==============================================================
# HELPERS
# ==============================================================


def to_mb(
    value: int | float,
) -> float:
    return (
        float(value)
        / (1024.0 ** 2)
    )


def linear_slope(
    times: list[float],
    values: list[float],
) -> float:
    if len(values) < 2:
        return 0.0

    count = len(values)

    mean_x = (
        sum(times)
        / count
    )

    mean_y = (
        sum(values)
        / count
    )

    numerator = sum(
        (
            x - mean_x
        )
        * (
            y - mean_y
        )
        for x, y in zip(
            times,
            values,
        )
    )

    denominator = sum(
        (
            x - mean_x
        ) ** 2
        for x in times
    )

    if denominator == 0.0:
        return 0.0

    return (
        numerator
        / denominator
    )


def get_process_tree(
    root_process: psutil.Process,
) -> list[psutil.Process]:
    """
    Return root process + all recursive children.
    """

    processes: list[
        psutil.Process
    ] = []

    try:
        if root_process.is_running():
            processes.append(
                root_process
            )

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
    ):
        pass

    try:
        children = (
            root_process.children(
                recursive=True
            )
        )

        processes.extend(
            children
        )

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
    ):
        pass

    return processes


def process_tree_memory(
    root_process: psutil.Process,
) -> tuple[
    float,
    float,
    float,
    list[
        tuple[
            int,
            str,
            float,
            float,
        ]
    ],
]:
    """
    Return total RSS/private/VMS across root + children.

    Also returns per-process details.
    """

    total_rss = 0.0
    total_private = 0.0
    total_vms = 0.0

    details: list[
        tuple[
            int,
            str,
            float,
            float,
        ]
    ] = []

    for process in get_process_tree(
        root_process
    ):
        try:
            memory = (
                process.memory_info()
            )

            rss_mb = to_mb(
                memory.rss
            )

            vms_mb = to_mb(
                memory.vms
            )

            private_mb = rss_mb

            try:
                full = (
                    process.memory_full_info()
                )

                private_value = getattr(
                    full,
                    "private",
                    None,
                )

                if private_value is not None:
                    private_mb = to_mb(
                        private_value
                    )

            except (
                psutil.Error,
                OSError,
            ):
                pass

            try:
                name = (
                    process.name()
                )

            except psutil.Error:
                name = "<unknown>"

            total_rss += (
                rss_mb
            )

            total_private += (
                private_mb
            )

            total_vms += (
                vms_mb
            )

            details.append(
                (
                    process.pid,
                    name,
                    rss_mb,
                    private_mb,
                )
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ):
            continue

    details.sort(
        key=lambda item: item[2],
        reverse=True,
    )

    return (
        total_rss,
        total_private,
        total_vms,
        details,
    )


def terminate_tree(
    root_process: psutil.Process,
) -> None:
    """
    Terminate children first, then root.
    """

    try:
        children = (
            root_process.children(
                recursive=True
            )
        )

    except psutil.Error:
        children = []

    for process in reversed(
        children
    ):
        try:
            process.terminate()

        except psutil.Error:
            pass

    try:
        root_process.terminate()

    except psutil.Error:
        pass

    _, alive = psutil.wait_procs(
        children + [root_process],
        timeout=5.0,
    )

    for process in alive:
        try:
            process.kill()

        except psutil.Error:
            pass


# ==============================================================
# MAIN
# ==============================================================


def main() -> None:
    if not EXAMPLE.is_file():
        raise FileNotFoundError(
            f"Example not found: "
            f"{EXAMPLE}"
        )

    print()
    print("=" * 82)
    print(" Nexora External Memory Watch")
    print("=" * 82)
    print()

    print(
        f"Executable: {sys.executable}"
    )

    print(
        f"Example:    {EXAMPLE}"
    )

    print(
        f"Duration:   "
        f"{DURATION_SECONDS:.0f}s"
    )

    print()

    command = [
        sys.executable,
        "-Xgil=0",
        str(
            EXAMPLE
        ),
    ]

    child = subprocess.Popen(
        command,
        cwd=ROOT,
    )

    root_process = psutil.Process(
        child.pid
    )

    print(
        f"Root PID: {child.pid}"
    )

    print()

    samples: list[
        tuple[
            float,
            float,
            float,
            float,
        ]
    ] = []

    known_pids: set[int] = set()

    start = (
        time.perf_counter()
    )

    # Prime CPU counters for every process discovered later.
    cpu_initialized: set[int] = set()

    try:
        while True:
            now = (
                time.perf_counter()
            )

            elapsed = (
                now
                - start
            )

            # --------------------------------------------------
            # Check whether entire tree disappeared
            # --------------------------------------------------

            processes = get_process_tree(
                root_process
            )

            if not processes:
                print()
                print(
                    "Process tree exited."
                )

                break

            # --------------------------------------------------
            # Discover new child processes
            # --------------------------------------------------

            current_pids = {
                process.pid
                for process in processes
            }

            new_pids = (
                current_pids
                - known_pids
            )

            for pid in sorted(
                new_pids
            ):
                try:
                    process = (
                        psutil.Process(
                            pid
                        )
                    )

                    print(
                        f"Discovered PID "
                        f"{pid}: "
                        f"{process.name()}"
                    )

                except psutil.Error:
                    pass

            known_pids |= (
                current_pids
            )

            if (
                elapsed
                >= DURATION_SECONDS
            ):
                print()
                print(
                    "Measurement duration reached."
                )

                break

            # --------------------------------------------------
            # Memory
            # --------------------------------------------------

            (
                rss_mb,
                private_mb,
                vms_mb,
                details,
            ) = process_tree_memory(
                root_process
            )

            # --------------------------------------------------
            # Total CPU
            # --------------------------------------------------

            total_cpu = 0.0

            for process in processes:
                try:
                    if (
                        process.pid
                        not in cpu_initialized
                    ):
                        process.cpu_percent(
                            interval=None
                        )

                        cpu_initialized.add(
                            process.pid
                        )

                    else:
                        total_cpu += (
                            process.cpu_percent(
                                interval=None
                            )
                        )

                except psutil.Error:
                    pass

            samples.append(
                (
                    elapsed,
                    rss_mb,
                    private_mb,
                    vms_mb,
                )
            )

            print(
                f"{elapsed:6.1f}s"
                f" | RSS: "
                f"{rss_mb:8.1f} MB"
                f" | Private: "
                f"{private_mb:8.1f} MB"
                f" | VMS: "
                f"{vms_mb:9.1f} MB"
                f" | CPU: "
                f"{total_cpu:5.1f}%"
                f" | Processes: "
                f"{len(details)}"
            )

            # --------------------------------------------------
            # Print largest process when there are children
            # --------------------------------------------------

            if details:
                (
                    largest_pid,
                    largest_name,
                    largest_rss,
                    largest_private,
                ) = details[0]

                print(
                    f"        largest: "
                    f"PID {largest_pid} "
                    f"{largest_name}"
                    f" | RSS "
                    f"{largest_rss:.1f} MB"
                    f" | Private "
                    f"{largest_private:.1f} MB"
                )

            time.sleep(
                SAMPLE_INTERVAL
            )

    finally:
        print()
        print(
            "Stopping process tree..."
        )

        terminate_tree(
            root_process
        )

    # ==========================================================
    # ANALYSIS
    # ==============================================================

    if len(samples) < 5:
        print()
        print(
            "Not enough samples."
        )

        return

    analysis = [
        sample
        for sample in samples
        if sample[0] >= 10.0
    ]

    if len(analysis) < 3:
        analysis = samples

    base_time = (
        analysis[0][0]
    )

    times = [
        item[0]
        - base_time
        for item in analysis
    ]

    rss_values = [
        item[1]
        for item in analysis
    ]

    private_values = [
        item[2]
        for item in analysis
    ]

    vms_values = [
        item[3]
        for item in analysis
    ]

    rss_growth = (
        rss_values[-1]
        - rss_values[0]
    )

    private_growth = (
        private_values[-1]
        - private_values[0]
    )

    vms_growth = (
        vms_values[-1]
        - vms_values[0]
    )

    rss_slope = linear_slope(
        times,
        rss_values,
    )

    private_slope = (
        linear_slope(
            times,
            private_values,
        )
    )

    vms_slope = linear_slope(
        times,
        vms_values,
    )

    print()
    print("=" * 82)
    print(" Memory Analysis")
    print("=" * 82)
    print()

    print(
        f"RSS start:       "
        f"{rss_values[0]:8.1f} MB"
    )

    print(
        f"RSS end:         "
        f"{rss_values[-1]:8.1f} MB"
    )

    print(
        f"RSS growth:      "
        f"{rss_growth:+8.1f} MB"
    )

    print(
        f"RSS slope:       "
        f"{rss_slope:+8.3f} MB/s"
    )

    print()

    print(
        f"Private start:   "
        f"{private_values[0]:8.1f} MB"
    )

    print(
        f"Private end:     "
        f"{private_values[-1]:8.1f} MB"
    )

    print(
        f"Private growth:  "
        f"{private_growth:+8.1f} MB"
    )

    print(
        f"Private slope:   "
        f"{private_slope:+8.3f} MB/s"
    )

    print()

    print(
        f"VMS growth:      "
        f"{vms_growth:+8.1f} MB"
    )

    print(
        f"VMS slope:       "
        f"{vms_slope:+8.3f} MB/s"
    )

    print()

    print(
        "Diagnosis:"
    )

    if private_slope >= 0.50:
        print(
            "  Strong continuous private-memory "
            "growth detected."
        )

    elif (
        rss_slope >= 0.50
        and private_slope < 0.20
    ):
        print(
            "  RSS is growing while private memory "
            "is comparatively stable."
        )

    elif (
        rss_slope < 0.20
        and private_slope < 0.20
    ):
        print(
            "  Process tree memory is stable."
        )

    else:
        print(
            "  Mild or mixed memory growth detected."
        )

    print()


if __name__ == "__main__":
    main()