from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes.node import Node


if TYPE_CHECKING:
    from nexora.ecs.world import World


class CollisionShape2D(Node):
    """
    Rectangular 2D collision shape.

    CollisionShape2D contains collision GEOMETRY only.

    It does not decide:
        - what it collides with
        - whether it blocks movement
        - whether it is a trigger

    Those responsibilities belong to the parent Body2D / Area2D.

    The transform represents the top-left corner of the shape.

    Currently only axis-aligned rectangles are supported.
    Rotation support can be added later with additional shape types.
    """

    def __init__(
        self,
        name: str,
        world: World,
        width: float = 32.0,
        height: float = 32.0,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self._width: float = 32.0
        self._height: float = 32.0

        self.disabled: bool = False

        self.set_size(
            width,
            height,
        )

    # ==============================================================
    # Size
    # ==============================================================

    @property
    def width(
        self,
    ) -> float:
        return self._width

    @width.setter
    def width(
        self,
        value: float,
    ) -> None:
        self.set_size(
            value,
            self._height,
        )

    @property
    def height(
        self,
    ) -> float:
        return self._height

    @height.setter
    def height(
        self,
        value: float,
    ) -> None:
        self.set_size(
            self._width,
            value,
        )

    def set_size(
        self,
        width: float,
        height: float,
    ) -> None:
        width = float(
            width
        )

        height = float(
            height
        )

        if width <= 0.0:
            raise ValueError(
                "CollisionShape2D width must be greater than zero."
            )

        if height <= 0.0:
            raise ValueError(
                "CollisionShape2D height must be greater than zero."
            )

        self._width = width
        self._height = height

    # ==============================================================
    # World geometry
    # ==============================================================

    @property
    def world_size(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        scale_x, scale_y = (
            self.world_scale
        )

        return (
            abs(
                self._width
                * scale_x
            ),
            abs(
                self._height
                * scale_y
            ),
        )

    @property
    def world_rect(
        self,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        """
        Return the shape rectangle in world coordinates.

        Result:
            x, y, width, height
        """

        x, y = (
            self.world_position
        )

        scale_x, scale_y = (
            self.world_scale
        )

        scaled_width = (
            self._width
            * scale_x
        )

        scaled_height = (
            self._height
            * scale_y
        )

        if scaled_width < 0.0:
            x += scaled_width

        if scaled_height < 0.0:
            y += scaled_height

        return (
            x,
            y,
            abs(
                scaled_width
            ),
            abs(
                scaled_height
            ),
        )

    # ==============================================================
    # Intersection
    # ==============================================================

    def overlaps(
        self,
        other: CollisionShape2D,
    ) -> bool:
        if self.disabled:
            return False

        if other.disabled:
            return False

        ax, ay, aw, ah = (
            self.world_rect
        )

        bx, by, bw, bh = (
            other.world_rect
        )

        return (
            ax < bx + bw
            and ax + aw > bx
            and ay < by + bh
            and ay + ah > by
        )

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        if self.disabled:
            return False

        rect_x, rect_y, width, height = (
            self.world_rect
        )

        x = float(
            x
        )

        y = float(
            y
        )

        return (
            rect_x <= x < rect_x + width
            and rect_y <= y < rect_y + height
        )