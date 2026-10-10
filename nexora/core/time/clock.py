from __future__ import annotations

import time as _time


class Time:
    """
    Central timing system for Nexora.

    Gameplay uses a fixed timestep while rendering can
    run independently at the configured frame rate.
    """

    def __init__(
        self,
        fixed_delta_time: float = 1.0 / 60.0,
        max_delta_time: float = 0.1,
    ):
        if fixed_delta_time <= 0:
            raise ValueError(
                "fixed_delta_time must be greater than 0."
            )

        if max_delta_time <= 0:
            raise ValueError(
                "max_delta_time must be greater than 0."
            )

        self.fixed_delta_time = fixed_delta_time
        self.max_delta_time = max_delta_time

        self.delta_time = 0.0
        self.unscaled_delta_time = 0.0

        self.fixed_delta_time_accumulator = 0.0

        self.total_time = 0.0
        self.fixed_time = 0.0

        self.frame = 0
        self.fixed_frame = 0

        self.time_scale = 1.0

        self._last_time = _time.perf_counter()

    def begin_frame(self) -> None:
        """
        Update timing information for a new rendered frame.
        """

        now = _time.perf_counter()

        raw_delta = now - self._last_time
        self._last_time = now

        raw_delta = min(
            raw_delta,
            self.max_delta_time,
        )

        self.unscaled_delta_time = raw_delta

        self.delta_time = (
            raw_delta * self.time_scale
        )

        self.total_time += self.delta_time

        self.fixed_delta_time_accumulator += self.delta_time

        self.frame += 1

    def should_fixed_update(self) -> bool:
        return (
            self.fixed_delta_time_accumulator
            >= self.fixed_delta_time
        )

    def consume_fixed_update(self) -> None:
        self.fixed_delta_time_accumulator -= (
            self.fixed_delta_time
        )

        self.fixed_time += self.fixed_delta_time

        self.fixed_frame += 1

    @property
    def interpolation(self) -> float:
        """
        Interpolation value between the last and next
        fixed update.
        """

        return (
            self.fixed_delta_time_accumulator
            / self.fixed_delta_time
        )

    def reset(self) -> None:
        now = _time.perf_counter()

        self._last_time = now

        self.delta_time = 0.0
        self.unscaled_delta_time = 0.0

        self.fixed_delta_time_accumulator = 0.0

        self.total_time = 0.0
        self.fixed_time = 0.0

        self.frame = 0
        self.fixed_frame = 0