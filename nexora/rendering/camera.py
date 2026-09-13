from __future__ import annotations

from dataclasses import dataclass
import random
import math


@dataclass(slots=True)
class Camera:
    """
    2D world camera for Nexora.

    The camera position represents the center of the visible
    screen in world coordinates.
    """

    x: float = 0.0
    y: float = 0.0

    zoom: float = 1.0
    rotation: float = 0.0

    # --------------------------------------------------------------
    # Smooth zoom
    # --------------------------------------------------------------

    target_zoom: float = 1.0
    zoom_speed: float = 8.0

    min_zoom: float = 0.25
    max_zoom: float = 3.0

    # --------------------------------------------------------------
    # World bounds
    # --------------------------------------------------------------

    min_x: float | None = None
    max_x: float | None = None
    min_y: float | None = None
    max_y: float | None = None

    # --------------------------------------------------------------
    # Dead zone
    # --------------------------------------------------------------

    dead_zone_width: float = 0.0
    dead_zone_height: float = 0.0

    # --------------------------------------------------------------
    # Screen shake
    # --------------------------------------------------------------

    shake_time: float = 0.0
    shake_duration: float = 0.0

    shake_strength: float = 0.0
    shake_max_strength: float = 0.0

    shake_x: float = 0.0
    shake_y: float = 0.0

    # --------------------------------------------------------------
    # Initialization
    # --------------------------------------------------------------

    def __post_init__(self) -> None:
        if self.zoom <= 0.0:
            raise ValueError(
                "Camera zoom must be greater than 0."
            )

        self.zoom = self._clamp_zoom(
            self.zoom
        )

        self.target_zoom = self.zoom

        if self.zoom_speed < 0.0:
            raise ValueError(
                "Camera zoom speed cannot be negative."
            )

    # ==============================================================
    # Position
    # ==============================================================

    def set_position(
        self,
        x: float,
        y: float,
    ) -> None:
        self.x = float(x)
        self.y = float(y)

    def move(
        self,
        dx: float,
        dy: float,
    ) -> None:
        self.x += dx
        self.y += dy

    def look_at(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Immediately center the camera on a world position.
        """

        self.x = float(x)
        self.y = float(y)

    # ==============================================================
    # Zoom
    # ==============================================================

    def _clamp_zoom(
        self,
        zoom: float,
    ) -> float:
        return max(
            self.min_zoom,
            min(
                self.max_zoom,
                zoom,
            ),
        )

    def set_zoom(
        self,
        zoom: float,
        *,
        immediate: bool = False,
    ) -> None:
        """
        Set the target zoom.

        By default the camera smoothly moves toward the
        requested zoom level.

        immediate=True changes the zoom instantly.
        """

        zoom = self._clamp_zoom(
            float(zoom)
        )

        self.target_zoom = zoom

        if immediate:
            self.zoom = zoom

    def zoom_by(
        self,
        amount: float,
        *,
        immediate: bool = False,
    ) -> None:
        """
        Change the target zoom relative to the current target.
        """

        self.set_zoom(
            self.target_zoom + amount,
            immediate=immediate,
        )

    def update_zoom(
        self,
        delta_time: float,
    ) -> None:
        """
        Smoothly move the current zoom toward target_zoom.
        """

        if self.zoom == self.target_zoom:
            return

        if self.zoom_speed <= 0.0:
            self.zoom = self.target_zoom
            return

        factor = 1.0 - pow(
            0.001,
            self.zoom_speed * delta_time,
        )

        self.zoom += (
            self.target_zoom - self.zoom
        ) * factor

        if abs(
            self.target_zoom - self.zoom
        ) < 0.0001:
            self.zoom = self.target_zoom

    # ==============================================================
    # Follow
    # ==============================================================

    def follow(
        self,
        x: float,
        y: float,
        smooth: float = 1.0,
        delta_time: float = 1.0 / 60.0,
    ) -> None:
        """
        Follow a world position.

        If a dead zone is configured, the camera only moves when
        the target leaves that zone.

        smooth=1.0 means immediate movement.
        Lower values produce smoother movement.
        """

        target_x = float(x)
        target_y = float(y)

        # ----------------------------------------------------------
        # Dead Zone
        # ----------------------------------------------------------

        half_dead_width = (
            self.dead_zone_width * 0.5
        )

        half_dead_height = (
            self.dead_zone_height * 0.5
        )

        desired_x = self.x
        desired_y = self.y

        if self.dead_zone_width <= 0.0:
            desired_x = target_x

        elif target_x < self.x - half_dead_width:
            desired_x = (
                target_x + half_dead_width
            )

        elif target_x > self.x + half_dead_width:
            desired_x = (
                target_x - half_dead_width
            )

        if self.dead_zone_height <= 0.0:
            desired_y = target_y

        elif target_y < self.y - half_dead_height:
            desired_y = (
                target_y + half_dead_height
            )

        elif target_y > self.y + half_dead_height:
            desired_y = (
                target_y - half_dead_height
            )

        # ----------------------------------------------------------
        # Movement
        # ----------------------------------------------------------

        if smooth >= 1.0:
            self.x = desired_x
            self.y = desired_y
            return

        if smooth <= 0.0:
            return

        factor = 1.0 - pow(
            1.0 - smooth,
            delta_time * 60.0,
        )

        self.x += (
            desired_x - self.x
        ) * factor

        self.y += (
            desired_y - self.y
        ) * factor

    # ==============================================================
    # Dead Zone
    # ==============================================================

    def set_dead_zone(
        self,
        width: float,
        height: float,
    ) -> None:
        if width < 0.0:
            raise ValueError(
                "Dead zone width cannot be negative."
            )

        if height < 0.0:
            raise ValueError(
                "Dead zone height cannot be negative."
            )

        self.dead_zone_width = float(width)
        self.dead_zone_height = float(height)

    def clear_dead_zone(self) -> None:
        self.dead_zone_width = 0.0
        self.dead_zone_height = 0.0

    # ==============================================================
    # Screen Shake
    # ==============================================================

    def shake(
        self,
        strength: float,
        duration: float,
    ) -> None:
        """
        Start or intensify screen shake.

        strength:
            Maximum shake offset in world units.

        duration:
            Shake duration in seconds.

        Calling shake() while another shake is active increases
        the strength and keeps the stronger value.
        """

        if strength <= 0.0:
            return

        if duration <= 0.0:
            return

        self.shake_strength = max(
            self.shake_strength,
            float(strength),
        )

        self.shake_max_strength = max(
            self.shake_max_strength,
            float(strength),
        )

        self.shake_duration = max(
            self.shake_duration,
            float(duration),
        )

        self.shake_time = max(
            self.shake_time,
            float(duration),
        )

    def update_shake(
        self,
        delta_time: float,
    ) -> None:
        """
        Update screen shake and calculate the current offset.
        """

        if self.shake_time <= 0.0:
            self.shake_x = 0.0
            self.shake_y = 0.0
            self.shake_strength = 0.0
            self.shake_max_strength = 0.0
            return

        self.shake_time -= delta_time

        if self.shake_time < 0.0:
            self.shake_time = 0.0

        # ----------------------------------------------------------
        # Fade shake over time
        # ----------------------------------------------------------

        if self.shake_duration > 0.0:
            fade = (
                self.shake_time
                / self.shake_duration
            )
        else:
            fade = 0.0

        self.shake_strength = (
            self.shake_max_strength
            * fade
        )

        # ----------------------------------------------------------
        # Random offset
        # ----------------------------------------------------------

        self.shake_x = (
            random.uniform(-1.0, 1.0)
            * self.shake_strength
        )

        self.shake_y = (
            random.uniform(-1.0, 1.0)
            * self.shake_strength
        )

        if self.shake_time <= 0.0:
            self.shake_x = 0.0
            self.shake_y = 0.0
            self.shake_strength = 0.0
            self.shake_max_strength = 0.0

    def stop_shake(self) -> None:
        """
        Immediately stop screen shake.
        """

        self.shake_time = 0.0
        self.shake_duration = 0.0
        self.shake_strength = 0.0
        self.shake_max_strength = 0.0

        self.shake_x = 0.0
        self.shake_y = 0.0

    # ==============================================================
    # Coordinate Conversion
    # ==============================================================

    def world_to_screen(
        self,
        x: float,
        y: float,
        screen_width: int,
        screen_height: int,
    ) -> tuple[float, float]:
        """
        Convert world coordinates to screen coordinates.
        """

        screen_center_x = (
            screen_width * 0.5
        )

        screen_center_y = (
            screen_height * 0.5
        )

        screen_x = (
            (x - self.x) * self.zoom
            + screen_center_x
            + self.shake_x * self.zoom
        )

        screen_y = (
            (y - self.y) * self.zoom
            + screen_center_y
            + self.shake_y * self.zoom
        )

        return screen_x, screen_y

    def screen_to_world(
        self,
        x: float,
        y: float,
        screen_width: int,
        screen_height: int,
    ) -> tuple[float, float]:
        """
        Convert screen coordinates to world coordinates.

        Screen shake is ignored because it is only a visual
        rendering offset.
        """

        screen_center_x = (
            screen_width * 0.5
        )

        screen_center_y = (
            screen_height * 0.5
        )

        world_x = (
            (
                x
                - screen_center_x
            )
            / self.zoom
            + self.x
        )

        world_y = (
            (
                y
                - screen_center_y
            )
            / self.zoom
            + self.y
        )

        return world_x, world_y

    # ==============================================================
    # World Bounds
    # ==============================================================

    def set_bounds(
        self,
        min_x: float | None = None,
        max_x: float | None = None,
        min_y: float | None = None,
        max_y: float | None = None,
    ) -> None:
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y

    def clear_bounds(self) -> None:
        self.min_x = None
        self.max_x = None
        self.min_y = None
        self.max_y = None

    def clamp(
        self,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """
        Clamp the camera to its configured world bounds.

        The visible camera area is taken into account based
        on the current zoom level.
        """

        half_width = (
            screen_width * 0.5
        ) / self.zoom

        half_height = (
            screen_height * 0.5
        ) / self.zoom

        if (
            self.min_x is not None
            and self.max_x is not None
        ):
            world_width = (
                self.max_x - self.min_x
            )

            if world_width <= half_width * 2.0:
                self.x = (
                    self.min_x
                    + world_width * 0.5
                )
            else:
                self.x = max(
                    self.x,
                    self.min_x + half_width,
                )

                self.x = min(
                    self.x,
                    self.max_x - half_width,
                )

        else:
            if self.min_x is not None:
                self.x = max(
                    self.x,
                    self.min_x + half_width,
                )

            if self.max_x is not None:
                self.x = min(
                    self.x,
                    self.max_x - half_width,
                )

        if (
            self.min_y is not None
            and self.max_y is not None
        ):
            world_height = (
                self.max_y - self.min_y
            )

            if world_height <= half_height * 2.0:
                self.y = (
                    self.min_y
                    + world_height * 0.5
                )
            else:
                self.y = max(
                    self.y,
                    self.min_y + half_height,
                )

                self.y = min(
                    self.y,
                    self.max_y - half_height,
                )

        else:
            if self.min_y is not None:
                self.y = max(
                    self.y,
                    self.min_y + half_height,
                )

            if self.max_y is not None:
                self.y = min(
                    self.y,
                    self.max_y - half_height,
                )

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Update all camera effects.
        """

        self.update_zoom(
            delta_time
        )

        self.update_shake(
            delta_time
        )

