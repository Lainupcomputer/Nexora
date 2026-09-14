from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes.entity.body_2d import (
    Body2D,
)


if TYPE_CHECKING:
    from nexora.ecs.world import World


class StaticBody2D(Body2D):
    """
    Immovable physics body.

    Typical uses:

        - walls
        - trees
        - rocks
        - buildings
        - furniture
        - world obstacles

    StaticBody2D may still be repositioned manually through
    its Node transform.

    "Static" means physics movement does not push this body.
    """

    def __init__(
        self,
        name: str,
        world: World,
    ) -> None:
        super().__init__(
            name,
            world,
        )