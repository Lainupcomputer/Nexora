from __future__ import annotations

import random

class CameraMotionEffectsMixin:

    def add_trauma(
        self,
        amount: float,
    ) -> None:
        """
        Add trauma to the camera.

        Trauma is clamped between 0 and 1.
        """

        self.trauma = self._clamp01(
            self.trauma
            + float(amount)
        )

    def set_trauma(
        self,
        amount: float,
    ) -> None:
        self.trauma = self._clamp01(
            amount
        )

    def clear_trauma(
        self,
    ) -> None:
        self.trauma = 0.0

    def _update_trauma(
        self,
        delta_time: float,
    ) -> None:
        if self.trauma <= 0.0:
            return

        amount = (
            self.trauma
            ** self.trauma_power
        )

        strength = (
            self.trauma_strength
            * amount
        )

        self.camera.shake_x += (
            random.uniform(
                -1.0,
                1.0,
            )
            * strength
        )

        self.camera.shake_y += (
            random.uniform(
                -1.0,
                1.0,
            )
            * strength
        )

        self.trauma = max(
            0.0,
            self.trauma
            - self.trauma_decay
            * delta_time,
        )

    def punch(
        self,
        x: float,
        y: float,
        *,
        duration: float = 0.15,
    ) -> None:
        """
        Apply a directional camera kick.

        Useful for weapon recoil, impacts or explosions.
        """

        duration = float(
            duration
        )

        if duration <= 0.0:
            return

        self._punch_x = float(
            x
        )

        self._punch_y = float(
            y
        )

        self._punch_duration = duration

        self._punch_elapsed = 0.0

        self._punch_active = True

    def stop_punch(
        self,
    ) -> None:
        self._punch_active = False

        self._punch_x = 0.0
        self._punch_y = 0.0

        self._punch_duration = 0.0
        self._punch_elapsed = 0.0

    def _update_punch(
        self,
        delta_time: float,
    ) -> None:
        if not self._punch_active:
            return

        self._punch_elapsed += (
            delta_time
        )

        progress = min(
            self._punch_elapsed
            / self._punch_duration,
            1.0,
        )

        decay = (
            1.0
            - self._ease(
                progress,
                "ease_out",
            )
        )

        self.camera.shake_x += (
            self._punch_x
            * decay
        )

        self.camera.shake_y += (
            self._punch_y
            * decay
        )

        if progress >= 1.0:
            self.stop_punch()
