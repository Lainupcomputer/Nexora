from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes.camera.camera_2d import Camera2D


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


class FixedCamera2D(Camera2D):
    """
    Fixed 2D camera.

    The camera stays at a fixed world position unless explicitly
    moved through its API.

    Typical use cases:

        - fixed rooms
        - arenas
        - boss fights
        - menu backgrounds
        - static gameplay views
    """

    def __init__(
        self,
        name: str,
        world,
        renderer: Renderer,
        *,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(
            name,
            world,
            renderer,
        )

        self._fixed_x = float(x)
        self._fixed_y = float(y)

        self.lock_position: bool = True

        self.set_position(
            self._fixed_x,
            self._fixed_y,
        )

    # ==========================================================
    # Fixed position
    # ==========================================================

    @property
    def fixed_position(
        self,
    ) -> tuple[float, float]:
        return (
            self._fixed_x,
            self._fixed_y,
        )

    def set_fixed_position(
        self,
        x: float,
        y: float,
        *,
        snap: bool = True,
    ) -> None:
        """
        Change the fixed world position.

        If snap is True, the camera immediately moves there.
        """

        self._fixed_x = float(x)
        self._fixed_y = float(y)

        if snap:
            self.set_position(
                self._fixed_x,
                self._fixed_y,
            )

            self.clamp()

    def reset_position(
        self,
    ) -> None:
        """
        Move camera back to the configured fixed position.
        """

        self.set_position(
            self._fixed_x,
            self._fixed_y,
        )

        self.clamp()

    # ==========================================================
    # Position lock
    # ==========================================================

    def lock(
        self,
    ) -> None:
        """
        Lock the camera to its fixed position.
        """

        self.lock_position = True

        self.reset_position()

    def unlock(
        self,
    ) -> None:
        """
        Allow the underlying camera position to be changed.
        """

        self.lock_position = False

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self.active:
            return

        if self.lock_position:
            self.set_position(
                self._fixed_x,
                self._fixed_y,
            )

        super().update(
            delta_time
        )