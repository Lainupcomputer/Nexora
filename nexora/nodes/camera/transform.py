from __future__ import annotations

class CameraTransformMixin:

    def set_position(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Set camera world position.
        """

        self.camera.set_position(
            float(x),
            float(y),
        )

    def move(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Move camera relative to its current position.
        """

        self.camera.move(
            float(x),
            float(y),
        )

    @property
    def zoom(self) -> float:
        return self.camera.zoom

    @zoom.setter
    def zoom(
        self,
        value: float,
    ) -> None:
        self.camera.set_zoom(
            float(value)
        )

    def set_zoom(
        self,
        zoom: float,
    ) -> None:
        self.camera.set_zoom(
            float(zoom)
        )

    def zoom_to(
        self,
        zoom: float,
    ) -> None:
        """
        Smoothly transition to a zoom level.
        """

        self.camera.zoom_to(
            float(zoom)
        )

    def set_bounds(
        self,
        min_x: float | None = None,
        max_x: float | None = None,
        min_y: float | None = None,
        max_y: float | None = None,
    ) -> None:
        self.camera.set_bounds(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
        )

    def clear_bounds(
        self,
    ) -> None:
        self.camera.clear_bounds()

    def clamp(
        self,
    ) -> None:
        if not self.clamp_to_bounds:
            return

        self.camera.clamp(
            self.renderer.width,
            self.renderer.height,
        )

    def set_dead_zone(
        self,
        width: float,
        height: float,
    ) -> None:
        """
        Set camera follow dead zone.
        """

        self.camera.set_dead_zone(
            float(width),
            float(height),
        )

    def clear_dead_zone(
        self,
    ) -> None:
        """
        Disable camera dead zone.
        """

        self.camera.clear_dead_zone()

    def shake(
        self,
        intensity: float,
        duration: float,
    ) -> None:
        """
        Start a traditional timed screen shake.
        """

        self.camera.shake(
            strength=float(
                intensity
            ),
            duration=float(
                duration
            ),
        )

    def stop_shake(
        self,
    ) -> None:
        """
        Stop traditional screen shake.
        """

        self.camera.stop_shake()

    def world_to_screen(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        return self.camera.world_to_screen(
            x,
            y,
            self.renderer.width,
            self.renderer.height,
        )

    def screen_to_world(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        return self.camera.screen_to_world(
            x,
            y,
            self.renderer.width,
            self.renderer.height,
        )
