from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from nexora.tilemap.constants import EMPTY_TILE
from nexora.tilemap.tilemap import TileMap
from nexora.tilemap.tileset import TileSet


GridPoint = tuple[int, int]
WorldPoint = tuple[float, float]


@dataclass(frozen=True, slots=True)
class NavigationPath:
    """Result of a tile navigation query."""

    tiles: tuple[GridPoint, ...]
    world_points: tuple[WorldPoint, ...]
    cost: float

    @property
    def found(self) -> bool:
        return bool(self.tiles)

    @property
    def length(self) -> int:
        return len(self.tiles)




class NavigationState:
    """Shared dynamic navigation state for a TileMapNode.

    Multiple TileNavigation instances may use the same state while keeping
    their own movement rules (diagonal movement, costs, layer, ...). Dynamic
    blockers therefore affect every agent bound to the same TileMapNode.
    """

    def __init__(self) -> None:
        self._dynamic_blockers: set[GridPoint] = set()
        self._owned_blockers: dict[int, set[GridPoint]] = {}
        self._revision: int = 0

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def dynamic_blockers(self) -> frozenset[GridPoint]:
        points = set(self._dynamic_blockers)
        for owned in self._owned_blockers.values():
            points.update(owned)
        return frozenset(points)

    def invalidate(self) -> None:
        self._revision += 1

    def is_blocked(self, x: int, y: int) -> bool:
        point = (int(x), int(y))
        if point in self._dynamic_blockers:
            return True
        return any(point in owned for owned in self._owned_blockers.values())

    def set_blocked(self, x: int, y: int, blocked: bool = True) -> bool:
        point = (int(x), int(y))
        changed = False

        if blocked:
            if point not in self._dynamic_blockers:
                self._dynamic_blockers.add(point)
                changed = True
        elif point in self._dynamic_blockers:
            self._dynamic_blockers.remove(point)
            changed = True

        if changed:
            self.invalidate()

        return changed

    def move_blocker(
        self,
        old: GridPoint | None,
        new: GridPoint | None,
    ) -> bool:
        old_point = None if old is None else (int(old[0]), int(old[1]))
        new_point = None if new is None else (int(new[0]), int(new[1]))

        if old_point == new_point:
            return False

        changed = False
        if old_point is not None and old_point in self._dynamic_blockers:
            self._dynamic_blockers.remove(old_point)
            changed = True
        if new_point is not None and new_point not in self._dynamic_blockers:
            self._dynamic_blockers.add(new_point)
            changed = True

        if changed:
            self.invalidate()
        return changed

    def set_owner_tiles(
        self,
        owner_id: int,
        points,
    ) -> bool:
        owner_id = int(owner_id)
        normalized = {
            (int(point[0]), int(point[1]))
            for point in points
        }
        previous = self._owned_blockers.get(owner_id, set())
        if previous == normalized:
            return False

        before = self.dynamic_blockers
        if normalized:
            self._owned_blockers[owner_id] = normalized
        else:
            self._owned_blockers.pop(owner_id, None)
        after = self.dynamic_blockers

        if before != after:
            self.invalidate()
        return True

    def clear_owner(self, owner_id: int) -> bool:
        return self.set_owner_tiles(int(owner_id), ())

    def clear_blockers(self) -> bool:
        if not self._dynamic_blockers and not self._owned_blockers:
            return False
        self._dynamic_blockers.clear()
        self._owned_blockers.clear()
        self.invalidate()
        return True


class TileNavigation:
    """A* navigation over a TileMap layer.

    Navigation is projection-independent. Orthogonal and isometric maps use
    the same tile-neighbour graph; only world/tile conversion differs.

    Walkability rules:
      - coordinates outside the map are blocked
      - dynamic blockers are blocked
      - empty cells follow ``empty_walkable``
      - TileMetadata.solid blocks a tile
      - metadata property ``navigation_cost`` controls traversal cost
    """

    ORTHOGONAL_DIRS: tuple[GridPoint, ...] = (
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
    )

    DIAGONAL_DIRS: tuple[GridPoint, ...] = (
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    )

    def __init__(
        self,
        tilemap: TileMap,
        tileset: TileSet,
        *,
        layer_name: str,
        allow_diagonal: bool = False,
        allow_corner_cutting: bool = False,
        empty_walkable: bool = True,
        default_cost: float = 1.0,
        cache_paths: bool = True,
        state: NavigationState | None = None,
    ) -> None:
        if tilemap.tile_size != tileset.tile_size:
            raise ValueError(
                "TileMap tile size does not match TileSet tile size."
            )

        default_cost = float(default_cost)
        if default_cost <= 0.0:
            raise ValueError("default_cost must be greater than zero.")

        tilemap.require_layer(layer_name)

        self.tilemap = tilemap
        self.tileset = tileset
        self.layer_name = str(layer_name)
        self.allow_diagonal = bool(allow_diagonal)
        self.allow_corner_cutting = bool(allow_corner_cutting)
        self.empty_walkable = bool(empty_walkable)
        self.default_cost = default_cost
        self.cache_paths = bool(cache_paths)

        self.state = state if state is not None else NavigationState()
        self._cache_revision = self.state.revision
        self._cache: dict[
            tuple[int, GridPoint, GridPoint, bool, bool], NavigationPath | None
        ] = {}

    @property
    def layer(self):
        return self.tilemap.require_layer(self.layer_name)

    @property
    def revision(self) -> int:
        return self.state.revision

    @property
    def dynamic_blockers(self) -> frozenset[GridPoint]:
        return self.state.dynamic_blockers

    def invalidate(self) -> None:
        """Invalidate cached paths after map/metadata changes."""
        self.state.invalidate()
        self._cache.clear()
        self._cache_revision = self.state.revision

    def _sync_cache_revision(self) -> None:
        if self._cache_revision != self.state.revision:
            self._cache.clear()
            self._cache_revision = self.state.revision

    def set_blocked(self, x: int, y: int, blocked: bool = True) -> None:
        point = (int(x), int(y))
        if not self.tilemap.contains(*point):
            raise IndexError(
                f"Tile coordinate {point} is outside TileMap size "
                f"{self.tilemap.width}x{self.tilemap.height}."
            )

        if self.state.set_blocked(*point, blocked=blocked):
            self._sync_cache_revision()

    def clear_blockers(self) -> None:
        if self.state.clear_blockers():
            self._sync_cache_revision()

    def tile_id(self, x: int, y: int) -> int:
        if not self.tilemap.contains(x, y):
            return EMPTY_TILE
        return self.layer.get_tile(int(x), int(y))

    def metadata_at(self, x: int, y: int):
        tile_id = self.tile_id(x, y)
        if tile_id == EMPTY_TILE:
            return None
        if not self.tileset.contains(tile_id):
            raise IndexError(
                f"Tile index {tile_id} at ({x}, {y}) is outside the TileSet."
            )
        return self.tileset.get_metadata(tile_id)

    def is_walkable(self, x: int, y: int) -> bool:
        x = int(x)
        y = int(y)

        if not self.tilemap.contains(x, y):
            return False
        if self.state.is_blocked(x, y):
            return False

        tile_id = self.layer.get_tile(x, y)
        if tile_id == EMPTY_TILE:
            return self.empty_walkable
        if not self.tileset.contains(tile_id):
            return False

        metadata = self.tileset.get_metadata(tile_id)
        if metadata is None:
            return True
        return metadata.walkable

    def traversal_cost(self, x: int, y: int) -> float:
        if not self.is_walkable(x, y):
            return math.inf

        metadata = self.metadata_at(x, y)
        if metadata is None:
            return self.default_cost

        raw = metadata.get_property("navigation_cost", self.default_cost)
        cost = float(raw)
        if cost <= 0.0 or not math.isfinite(cost):
            raise ValueError(
                f"navigation_cost at ({x}, {y}) must be finite and > 0."
            )
        return cost

    def neighbors(self, x: int, y: int) -> tuple[tuple[int, int, float], ...]:
        x = int(x)
        y = int(y)
        result: list[tuple[int, int, float]] = []

        for dx, dy in self.ORTHOGONAL_DIRS:
            nx = x + dx
            ny = y + dy
            if self.is_walkable(nx, ny):
                result.append((nx, ny, self.traversal_cost(nx, ny)))

        if self.allow_diagonal:
            for dx, dy in self.DIAGONAL_DIRS:
                nx = x + dx
                ny = y + dy
                if not self.is_walkable(nx, ny):
                    continue

                if not self.allow_corner_cutting:
                    if not (
                        self.is_walkable(x + dx, y)
                        and self.is_walkable(x, y + dy)
                    ):
                        continue

                result.append(
                    (nx, ny, self.traversal_cost(nx, ny) * math.sqrt(2.0))
                )

        return tuple(result)

    def _heuristic(self, a: GridPoint, b: GridPoint) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        if self.allow_diagonal:
            diagonal = min(dx, dy)
            straight = max(dx, dy) - diagonal
            return self.default_cost * (
                diagonal * math.sqrt(2.0) + straight
            )
        return self.default_cost * (dx + dy)

    def find_path(
        self,
        start: GridPoint,
        goal: GridPoint,
        *,
        allow_blocked_start: bool = True,
        allow_blocked_goal: bool = False,
    ) -> NavigationPath | None:
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))

        self._sync_cache_revision()

        if not self.tilemap.contains(*start) or not self.tilemap.contains(*goal):
            return None
        if start == goal:
            if self.is_walkable(*start) or allow_blocked_start:
                world = self.tilemap.tile_to_world(*start)
                return NavigationPath((start,), (world,), 0.0)
            return None
        if not allow_blocked_start and not self.is_walkable(*start):
            return None
        if not allow_blocked_goal and not self.is_walkable(*goal):
            return None

        cache_key = (
            self.revision,
            start,
            goal,
            allow_blocked_start,
            allow_blocked_goal,
        )
        if self.cache_paths and cache_key in self._cache:
            return self._cache[cache_key]

        open_heap: list[tuple[float, float, int, GridPoint]] = []
        sequence = 0
        heapq.heappush(open_heap, (self._heuristic(start, goal), 0.0, sequence, start))

        came_from: dict[GridPoint, GridPoint] = {}
        g_score: dict[GridPoint, float] = {start: 0.0}
        closed: set[GridPoint] = set()

        while open_heap:
            _, current_cost, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            if current == goal:
                path = self._build_path(came_from, current, current_cost)
                if self.cache_paths:
                    self._cache[cache_key] = path
                return path

            closed.add(current)

            for nx, ny, step_cost in self.neighbors(*current):
                neighbor = (nx, ny)
                if neighbor in closed:
                    continue
                tentative = current_cost + step_cost
                if tentative >= g_score.get(neighbor, math.inf):
                    continue

                came_from[neighbor] = current
                g_score[neighbor] = tentative
                sequence += 1
                heapq.heappush(
                    open_heap,
                    (
                        tentative + self._heuristic(neighbor, goal),
                        tentative,
                        sequence,
                        neighbor,
                    ),
                )

        if self.cache_paths:
            self._cache[cache_key] = None
        return None

    def _build_path(
        self,
        came_from: dict[GridPoint, GridPoint],
        current: GridPoint,
        cost: float,
    ) -> NavigationPath:
        tiles = [current]
        while current in came_from:
            current = came_from[current]
            tiles.append(current)
        tiles.reverse()

        tile_tuple = tuple(tiles)
        return NavigationPath(
            tiles=tile_tuple,
            world_points=tuple(
                self.tilemap.tile_to_world(x, y) for x, y in tile_tuple
            ),
            cost=float(cost),
        )

    def find_world_path(
        self,
        start_x: float,
        start_y: float,
        goal_x: float,
        goal_y: float,
        **kwargs,
    ) -> NavigationPath | None:
        start = self.tilemap.world_to_tile(start_x, start_y)
        goal = self.tilemap.world_to_tile(goal_x, goal_y)
        return self.find_path(start, goal, **kwargs)
