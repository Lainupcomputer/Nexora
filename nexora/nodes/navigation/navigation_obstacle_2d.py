from __future__ import annotations

from nexora.nodes.node import Node
from nexora.nodes.world.tilemap_node import TileMapNode


class NavigationObstacle2D(Node):
    """Dynamic tile-navigation blocker.

    The obstacle does not perform physics collision. It only marks one or more
    TileMap cells as temporarily blocked for TileNavigation instances created
    from the same TileMapNode.

    The node can be placed directly in the scene or attached to a moving node.
    Its world position is converted to a tile every update. When it changes
    cells, the shared NavigationState revision changes and NavigationAgent2D
    instances automatically re-path.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.map_node: TileMapNode | None = None
        self.map_node_name: str | None = None

        # Square tile footprint. radius_tiles=0 blocks exactly one tile,
        # radius_tiles=1 blocks a 3x3 area, etc.
        self.radius_tiles: int = 0
        self.blocking_enabled: bool = True

        self._blocked_tiles: frozenset[tuple[int, int]] = frozenset()
        self._owner_id: int = id(self)

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def configure(self, map_node: TileMapNode) -> None:
        if map_node.tilemap is None:
            raise RuntimeError("TileMapNode must have a TileMap.")

        if self.map_node is not None and self.map_node is not map_node:
            self._clear_blocking()

        self.map_node = map_node
        self.map_node_name = map_node.name
        self.sync_blocking()

    def _try_lazy_bind(self) -> bool:
        if self.map_node is not None:
            return True
        if not self.map_node_name:
            return False

        root = self.tree_root
        node = root if root.name == self.map_node_name else root.find_child(
            self.map_node_name
        )
        if not isinstance(node, TileMapNode):
            return False

        self.map_node = node
        return True

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------

    @property
    def blocked_tiles(self) -> frozenset[tuple[int, int]]:
        return self._blocked_tiles

    @property
    def current_tile(self) -> tuple[int, int] | None:
        if not self._blocked_tiles:
            return None
        if self.radius_tiles == 0:
            return next(iter(self._blocked_tiles))
        if not self._try_lazy_bind() or self.map_node is None:
            return None
        x, y = self.world_position
        return self.map_node.world_to_tile(x, y)

    def set_blocking_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.blocking_enabled:
            return
        self.blocking_enabled = enabled
        self.sync_blocking()

    def _tiles_for_position(self) -> set[tuple[int, int]]:
        if self.map_node is None or self.map_node.tilemap is None:
            return set()

        world_x, world_y = self.world_position
        center_x, center_y = self.map_node.world_to_tile(world_x, world_y)
        tilemap = self.map_node.tilemap
        radius = max(int(self.radius_tiles), 0)

        result: set[tuple[int, int]] = set()
        for y in range(center_y - radius, center_y + radius + 1):
            for x in range(center_x - radius, center_x + radius + 1):
                if tilemap.contains(x, y):
                    result.add((x, y))
        return result

    def sync_blocking(self) -> bool:
        if not self._try_lazy_bind() or self.map_node is None:
            return False

        tiles = self._tiles_for_position() if self.blocking_enabled else set()
        before = self._blocked_tiles

        self.map_node.navigation_state.set_owner_tiles(
            self._owner_id,
            tiles,
        )
        self._blocked_tiles = frozenset(tiles)
        return before != self._blocked_tiles

    def _clear_blocking(self) -> None:
        if self.map_node is not None:
            self.map_node.navigation_state.clear_owner(self._owner_id)
        self._blocked_tiles = frozenset()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update(self, delta_time: float) -> None:
        del delta_time
        self.sync_blocking()

    def destroy(self) -> None:
        self._clear_blocking()
        super().destroy()
