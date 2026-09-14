from __future__ import annotations

import os
import time
from dataclasses import dataclass

import psutil

try:
    import pynvml
except ImportError:
    pynvml = None


# ==============================================================
# GPU METRICS
# ==============================================================


@dataclass(slots=True)
class GPUMetrics:
    device_name: str | None = None

    # Current Nexora / game process only.
    process_load_percent: float | None = None
    process_memory_mb: float | None = None


# ==============================================================
# NVIDIA PROVIDER
# ==============================================================


class NvidiaMetricsProvider:
    """
    NVIDIA per-process metrics provider using NVML.

    The provider attempts to measure only the current Nexora/game
    process instead of total system GPU usage.

    Depending on the NVIDIA driver and operating system,
    per-process GPU utilization may not be available.

    In that case:

        process_load_percent = None

    Per-process GPU memory is queried independently.
    """

    def __init__(
        self,
        *,
        interval: float = 0.5,
    ) -> None:
        self.interval = max(
            float(interval),
            0.1,
        )

        self.pid = os.getpid()

        self.metrics = GPUMetrics()

        self.available = False

        self._initialized = False
        self._device = None

        self._last_update = 0.0

        # NVML uses a microsecond timestamp for process
        # utilization samples.
        self._last_utilization_timestamp = 0

        self._initialize()

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def _initialize(
        self,
    ) -> None:
        if pynvml is None:
            return

        try:
            pynvml.nvmlInit()

            device_count = (
                pynvml.nvmlDeviceGetCount()
            )

            if device_count <= 0:
                return

            # --------------------------------------------------
            # Current implementation uses the first NVIDIA GPU.
            #
            # Later this can be mapped directly against the
            # SDL_GPU adapter selected by Nexora.
            # --------------------------------------------------

            self._device = (
                pynvml.nvmlDeviceGetHandleByIndex(
                    0
                )
            )

            name = (
                pynvml.nvmlDeviceGetName(
                    self._device
                )
            )

            if isinstance(
                name,
                bytes,
            ):
                name = name.decode(
                    "utf-8",
                    errors="replace",
                )

            self.metrics.device_name = str(
                name
            )

            self.available = True
            self._initialized = True

        except Exception:
            self.available = False
            self._initialized = False
            self._device = None

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
    ) -> GPUMetrics:
        if not self._initialized:
            return self.metrics

        now = time.perf_counter()

        if (
            now - self._last_update
            < self.interval
        ):
            return self.metrics

        self._last_update = now

        # Reset dynamic values so unsupported/stale data is not
        # accidentally displayed forever.
        self.metrics.process_load_percent = None
        self.metrics.process_memory_mb = None

        self._update_process_memory()
        self._update_process_utilization()

        return self.metrics

    # ==========================================================
    # PROCESS GPU MEMORY
    # ==========================================================

    def _update_process_memory(
        self,
    ) -> None:
        if (
            pynvml is None
            or self._device is None
        ):
            return

        process_memory = 0
        found_process = False

        # ------------------------------------------------------
        # Graphics processes
        # ------------------------------------------------------

        try:
            processes = (
                pynvml.nvmlDeviceGetGraphicsRunningProcesses(
                    self._device
                )
            )

            for process in processes:
                if (
                    int(process.pid)
                    != self.pid
                ):
                    continue

                used = getattr(
                    process,
                    "usedGpuMemory",
                    None,
                )

                if (
                    used is not None
                    and int(used) >= 0
                ):
                    process_memory += int(
                        used
                    )

                    found_process = True

        except Exception:
            pass

        # ------------------------------------------------------
        # Compute processes
        #
        # Only used as fallback because a process could otherwise
        # appear in both lists and be counted twice.
        # ------------------------------------------------------

        if not found_process:
            try:
                processes = (
                    pynvml.nvmlDeviceGetComputeRunningProcesses(
                        self._device
                    )
                )

                for process in processes:
                    if (
                        int(process.pid)
                        != self.pid
                    ):
                        continue

                    used = getattr(
                        process,
                        "usedGpuMemory",
                        None,
                    )

                    if (
                        used is not None
                        and int(used) >= 0
                    ):
                        process_memory += int(
                            used
                        )

                        found_process = True

            except Exception:
                pass

        if not found_process:
            return

        self.metrics.process_memory_mb = (
            process_memory
            / (1024.0 ** 2)
        )

    # ==========================================================
    # PROCESS GPU LOAD
    # ==========================================================

    def _update_process_utilization(
        self,
    ) -> None:
        """
        Read utilization belonging only to the current process.

        Some NVIDIA drivers / Windows WDDM configurations do not
        expose this through NVML.

        In that case the result remains None.
        """

        if (
            pynvml is None
            or self._device is None
        ):
            return

        try:
            samples = (
                pynvml.nvmlDeviceGetProcessUtilization(
                    self._device,
                    self._last_utilization_timestamp,
                )
            )

        except Exception:
            return

        if not samples:
            return

        latest_sample = None

        for sample in samples:
            timestamp = int(
                getattr(
                    sample,
                    "timeStamp",
                    0,
                )
            )

            if (
                timestamp
                > self._last_utilization_timestamp
            ):
                self._last_utilization_timestamp = (
                    timestamp
                )

            sample_pid = int(
                getattr(
                    sample,
                    "pid",
                    -1,
                )
            )

            if sample_pid != self.pid:
                continue

            if latest_sample is None:
                latest_sample = sample
                continue

            current_timestamp = int(
                getattr(
                    latest_sample,
                    "timeStamp",
                    0,
                )
            )

            if timestamp > current_timestamp:
                latest_sample = sample

        if latest_sample is None:
            return

        utilization = getattr(
            latest_sample,
            "smUtil",
            None,
        )

        if utilization is None:
            return

        try:
            self.metrics.process_load_percent = max(
                0.0,
                min(
                    float(utilization),
                    100.0,
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        if not self._initialized:
            return

        if pynvml is None:
            return

        try:
            pynvml.nvmlShutdown()

        except Exception:
            pass

        self._initialized = False
        self._device = None


# ==============================================================
# DEBUG SNAPSHOT
# ==============================================================


@dataclass(slots=True)
class DebugSnapshot:
    fps: float = 0.0

    frame_time_ms: float = 0.0
    delta_time: float = 0.0

    # CPU currently remains system CPU utilization.
    cpu_percent: float = 0.0

    # RAM used by the current Nexora/game process only.
    ram_used_mb: float = 0.0

    gpu_device_name: str | None = None

    # Current Nexora/game process only.
    gpu_process_load_percent: float | None = None
    gpu_process_memory_mb: float | None = None


# ==============================================================
# DEBUG METRICS
# ==============================================================


class DebugMetrics:
    """
    Runtime metrics collector used by Nexora's global F3 overlay.
    """

    def __init__(
        self,
        *,
        system_interval: float = 0.5,
    ) -> None:
        self.system_interval = max(
            float(system_interval),
            0.1,
        )

        self.snapshot = (
            DebugSnapshot()
        )

        # Current Nexora / game process.
        self._process = psutil.Process(
            os.getpid()
        )

        self._last_system_update = 0.0

        self._smoothed_fps = 0.0

        self._gpu = (
            NvidiaMetricsProvider(
                interval=0.5,
            )
        )

        # Prime CPU measurement.
        psutil.cpu_percent(
            interval=None
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> DebugSnapshot:
        delta_time = max(
            float(delta_time),
            0.0,
        )

        self.snapshot.delta_time = (
            delta_time
        )

        self.snapshot.frame_time_ms = (
            delta_time
            * 1000.0
        )

        # ------------------------------------------------------
        # FPS
        # ------------------------------------------------------

        if delta_time > 0.0:
            instant_fps = (
                1.0
                / delta_time
            )

            if (
                self._smoothed_fps
                <= 0.0
            ):
                self._smoothed_fps = (
                    instant_fps
                )

            else:
                self._smoothed_fps += (
                    instant_fps
                    - self._smoothed_fps
                ) * 0.10

            self.snapshot.fps = (
                self._smoothed_fps
            )

        # ------------------------------------------------------
        # CPU / RAM
        # ------------------------------------------------------

        now = time.perf_counter()

        if (
            now
            - self._last_system_update
            >= self.system_interval
        ):
            self._last_system_update = (
                now
            )

            self._update_system_metrics()

        # ------------------------------------------------------
        # GPU
        # ------------------------------------------------------

        gpu = self._gpu.update()

        self.snapshot.gpu_device_name = (
            gpu.device_name
        )

        self.snapshot.gpu_process_load_percent = (
            gpu.process_load_percent
        )

        self.snapshot.gpu_process_memory_mb = (
            gpu.process_memory_mb
        )

        return self.snapshot

    # ==========================================================
    # SYSTEM / PROCESS METRICS
    # ==========================================================

    def _update_system_metrics(
        self,
    ) -> None:
        # ------------------------------------------------------
        # CPU
        #
        # Currently system-wide CPU utilization.
        # ------------------------------------------------------

        self.snapshot.cpu_percent = float(
            psutil.cpu_percent(
                interval=None
            )
        )

        # ------------------------------------------------------
        # RAM
        #
        # Current Nexora/game process only.
        #
        # RSS represents the physical memory currently resident
        # for this process.
        # ------------------------------------------------------

        try:
            memory_info = (
                self._process.memory_info()
            )

            self.snapshot.ram_used_mb = (
                memory_info.rss
                / (1024.0 ** 2)
            )

        except (
            psutil.Error,
            OSError,
        ):
            self.snapshot.ram_used_mb = 0.0

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        self._gpu.shutdown()