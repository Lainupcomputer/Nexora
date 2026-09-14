from __future__ import annotations

import math
import weakref

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nexora.ecs.world import World
    from nexora.nodes.entity.body_2d import Body2D
    from nexora.nodes.node import Node


Cell = tuple[int, int]
AABB = tuple[
    float,
    float,
    float,
    float,
]


class PhysicsWorld2D:
    """
    Physics registry and spatial broadphase for one ECS World.

    Body2D nodes register themselves here.

    Bodies are stored in a spatial hash so collision queries do not
    need to traverse the complete Node tree.

    This class is an engine service and NOT a Node.
    """

    def __init__(
        self,
        world: World,
        *,
        cell_size: float = 128.0,
    ) -> None:
        cell_size = float(
            cell_size
        )

        if cell_size <= 0.0:
            raise ValueError(
                "cell_size must be greater than zero."
            )

        self.world = world
        self.cell_size = cell_size

        # All registered physics bodies.
        self._bodies: weakref.WeakSet[
            Body2D
        ] = weakref.WeakSet()

        # Spatial hash:
        #
        # (cell_x, cell_y) -> bodies
        self._grid: dict[
            Cell,
            set[Body2D],
        ] = {}

        # Reverse lookup:
        #
        # body -> occupied cells
        self._body_cells: weakref.WeakKeyDictionary[
            Body2D,
            set[Cell],
        ] = weakref.WeakKeyDictionary()

        self._dirty: bool = True

    # ==============================================================
    # Registration
    # ==============================================================

    def register(
        self,
        body: Body2D,
    ) -> None:
        if body.world is not self.world:
            raise ValueError(
                "Body belongs to a different ECS World."
            )

        self._bodies.add(
            body
        )

        self._dirty = True

    def unregister(
        self,
        body: Body2D,
    ) -> None:
        self._remove_from_grid(
            body
        )

        self._bodies.discard(
            body
        )

    # ==============================================================
    # State
    # ==============================================================

    @property
    def bodies(
        self,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        return tuple(
            self._bodies
        )

    @property
    def body_count(
        self,
    ) -> int:
        return len(
            self._bodies
        )

    @property
    def cell_count(
        self,
    ) -> int:
        return len(
            self._grid
        )

    def mark_dirty(
        self,
    ) -> None:
        self._dirty = True

    # ==============================================================
    # Rebuild
    # ==============================================================

    def rebuild(
        self,
    ) -> None:
        """
        Rebuild the complete broadphase.

        Scene calls this once before each fixed physics step.

        This also catches bodies moved through direct transform
        modification.
        """

        self._grid.clear()
        self._body_cells.clear()

        for body in tuple(
            self._bodies
        ):
            self._insert_body(
                body
            )

        self._dirty = False

    def ensure_ready(
        self,
    ) -> None:
        """
        Lazily build the registry when physics is used outside the
        normal Scene fixed-update lifecycle.
        """

        if self._dirty:
            self.rebuild()

    # ==============================================================
    # Single body synchronization
    # ==============================================================

    def update_body(
        self,
        body: Body2D,
    ) -> None:
        """
        Update one body's spatial proxy.

        CharacterBody2D uses this after movement.
        """

        if body not in self._bodies:
            self.register(
                body
            )

        self._remove_from_grid(
            body
        )

        self._insert_body(
            body
        )

    # ==============================================================
    # Query
    # ==============================================================

    def query_aabb(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        exclude: Body2D | None = None,
        tree_root: Node | None = None,
    ) -> tuple[
        Body2D,
        ...,
    ]:
        """
        Return physics bodies potentially intersecting an AABB.

        This is broadphase only.

        Exact CollisionShape2D checks still happen afterwards.
        """

        self.ensure_ready()

        width = float(
            width
        )

        height = float(
            height
        )

        if width < 0.0:
            raise ValueError(
                "query width must be >= 0."
            )

        if height < 0.0:
            raise ValueError(
                "query height must be >= 0."
            )

        cells = self._cells_for_aabb(
            float(
                x
            ),
            float(
                y
            ),
            width,
            height,
        )

        found: set[
            Body2D
        ] = set()

        for cell in cells:
            bodies = self._grid.get(
                cell
            )

            if bodies is None:
                continue

            for body in bodies:
                if body is exclude:
                    continue

                if tree_root is not None:
                    if body.tree_root is not tree_root:
                        continue

                found.add(
                    body
                )

        return tuple(
            found
        )

    # ==============================================================
    # Grid insertion
    # ==============================================================

    def _insert_body(
        self,
        body: Body2D,
    ) -> None:
        if not body.enabled:
            return

        if not body.collision_enabled:
            return

        aabb = (
            body.collision_aabb
        )

        if aabb is None:
            return

        x, y, width, height = (
            aabb
        )

        cells = self._cells_for_aabb(
            x,
            y,
            width,
            height,
        )

        if not cells:
            return

        self._body_cells[
            body
        ] = cells

        for cell in cells:
            bucket = self._grid.setdefault(
                cell,
                set(),
            )

            bucket.add(
                body
            )

    def _remove_from_grid(
        self,
        body: Body2D,
    ) -> None:
        cells = self._body_cells.pop(
            body,
            None,
        )

        if not cells:
            return

        for cell in cells:
            bucket = self._grid.get(
                cell
            )

            if bucket is None:
                continue

            bucket.discard(
                body
            )

            if not bucket:
                del self._grid[
                    cell
                ]

    # ==============================================================
    # Cell calculation
    # ==============================================================

    def _cells_for_aabb(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> set[
        Cell
    ]:
        if width <= 0.0:
            return set()

        if height <= 0.0:
            return set()

        epsilon = 1e-9

        left = math.floor(
            x
            / self.cell_size
        )

        top = math.floor(
            y
            / self.cell_size
        )

        right = math.floor(
            (
                x
                + width
                - epsilon
            )
            / self.cell_size
        )

        bottom = math.floor(
            (
                y
                + height
                - epsilon
            )
            / self.cell_size
        )

        result: set[
            Cell
        ] = set()

        for cell_y in range(
            top,
            bottom + 1,
        ):
            for cell_x in range(
                left,
                right + 1,
            ):
                result.add(
                    (
                        cell_x,
                        cell_y,
                    )
                )

        return result


# ==================================================================
# PhysicsWorld2D lookup
# ==================================================================

_PHYSICS_WORLDS: weakref.WeakKeyDictionary[
    World,
    PhysicsWorld2D,
] = weakref.WeakKeyDictionary()


def get_physics_world(
    world: World,
) -> PhysicsWorld2D:
    """
    Return the PhysicsWorld2D belonging to an ECS World.

    Created lazily on first use.
    """

    physics = _PHYSICS_WORLDS.get(
        world
    )

    if physics is None:
        physics = PhysicsWorld2D(
            world
        )

        _PHYSICS_WORLDS[
            world
        ] = physics

    return physics