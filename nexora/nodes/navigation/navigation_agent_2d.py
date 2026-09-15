from __future__ import annotations

import math
from typing import Callable

from nexora.nodes.node import Node
from nexora.nodes.entity.character_body_2d import CharacterBody2D
from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.tilemap.navigation import NavigationPath, TileNavigation


AgentCallback = Callable[["NavigationAgent2D"], None]


class NavigationAgent2D(Node):
    """Path-following helper node for CharacterBody2D.

    The agent computes and tracks a path, but it never moves the body by
    itself. Game code can query :attr:`desired_direction` or
    :meth:`desired_velocity` and apply that to the parent CharacterBody2D.

    A typical hierarchy is::

        CharacterBody2D
        └── NavigationAgent2D

    The agent can be configured directly with a TileMapNode, or lazily by
    setting ``map_node_name``. Lazy lookup is useful for serialized scenes,
    because all nodes may not yet exist while properties are restored.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.map_node: TileMapNode | None = None
        self.map_node_name: str | None = None
        self.layer_name: str = "ground"

        self.allow_diagonal: bool = False
        self.allow_corner_cutting: bool = False
        self.empty_walkable: bool = True
        self.default_cost: float = 1.0
        self.cache_paths: bool = True

        self.waypoint_tolerance: float = 4.0
        self.target_tolerance: float = 4.0
        self.auto_repath: bool = True
        self.repath_interval: float = 0.25

        # Local crowd avoidance. This adjusts the preferred path velocity
        # without modifying the global A* path.
        self.avoidance_enabled: bool = True
        self.avoidance_radius: float = 12.0
        self.avoidance_neighbor_distance: float = 64.0
        self.avoidance_time_horizon: float = 0.75
        self.avoidance_strength: float = 1.0
        self._avoidance_owner_id: int = id(self)

        self.navigation: TileNavigation | None = None
        self.path: NavigationPath | None = None
        self._world_points: tuple[tuple[float, float], ...] = ()
        self._path_index: int = 0

        self.target_position: tuple[float, float] | None = None
        self._target_dirty: bool = False
        self._repath_elapsed: float = 0.0
        self._last_navigation_revision: int = -1

        self._target_reached: bool = False
        self._navigation_failed: bool = False

        self._path_changed_callbacks: list[AgentCallback] = []
        self._target_reached_callbacks: list[AgentCallback] = []
        self._navigation_failed_callbacks: list[AgentCallback] = []

    # ------------------------------------------------------------------
    # Body / map binding
    # ------------------------------------------------------------------

    @property
    def body(self) -> CharacterBody2D | None:
        current = self.parent
        while current is not None:
            if isinstance(current, CharacterBody2D):
                return current
            current = current.parent
        return None

    def configure(
        self,
        map_node: TileMapNode,
        *,
        layer_name: str = "ground",
        allow_diagonal: bool | None = None,
        allow_corner_cutting: bool | None = None,
        empty_walkable: bool | None = None,
        default_cost: float | None = None,
        cache_paths: bool | None = None,
    ) -> TileNavigation:
        if map_node.tilemap is None or map_node.tileset is None:
            raise RuntimeError("TileMapNode must have a TileMap and TileSet.")

        if self.map_node is not None and self.map_node is not map_node:
            self._unregister_avoidance()

        self.map_node = map_node
        self.map_node_name = map_node.name
        self.layer_name = str(layer_name)

        if allow_diagonal is not None:
            self.allow_diagonal = bool(allow_diagonal)
        if allow_corner_cutting is not None:
            self.allow_corner_cutting = bool(allow_corner_cutting)
        if empty_walkable is not None:
            self.empty_walkable = bool(empty_walkable)
        if default_cost is not None:
            self.default_cost = float(default_cost)
        if cache_paths is not None:
            self.cache_paths = bool(cache_paths)

        self.navigation = map_node.create_navigation(
            layer_name=self.layer_name,
            allow_diagonal=self.allow_diagonal,
            allow_corner_cutting=self.allow_corner_cutting,
            empty_walkable=self.empty_walkable,
            default_cost=self.default_cost,
            cache_paths=self.cache_paths,
        )
        self._last_navigation_revision = self.navigation.revision
        self._target_dirty = self.target_position is not None
        self._sync_avoidance_agent()
        return self.navigation

    def set_navigation(
        self,
        navigation: TileNavigation,
        *,
        map_node: TileMapNode | None = None,
    ) -> None:
        self.navigation = navigation
        self.map_node = map_node
        if map_node is not None:
            self.map_node_name = map_node.name
        self.layer_name = navigation.layer_name
        self.allow_diagonal = navigation.allow_diagonal
        self.allow_corner_cutting = navigation.allow_corner_cutting
        self.empty_walkable = navigation.empty_walkable
        self.default_cost = navigation.default_cost
        self.cache_paths = navigation.cache_paths
        self._last_navigation_revision = navigation.revision
        self._target_dirty = self.target_position is not None
        self._sync_avoidance_agent()

    def _try_lazy_bind(self) -> bool:
        if self.navigation is not None:
            return True
        if not self.map_node_name:
            return False

        root = self.tree_root
        node = root if root.name == self.map_node_name else root.find_child(self.map_node_name)
        if not isinstance(node, TileMapNode):
            return False

        self.configure(node, layer_name=self.layer_name)
        return True

    # ------------------------------------------------------------------
    # Target / path
    # ------------------------------------------------------------------

    def set_target_position(self, x: float, y: float) -> None:
        self.target_position = (float(x), float(y))
        self._target_dirty = True
        self._target_reached = False
        self._navigation_failed = False

    def clear_target(self) -> None:
        self.target_position = None
        self.path = None
        self._world_points = ()
        self._path_index = 0
        self._target_dirty = False
        self._target_reached = False
        self._navigation_failed = False

    @property
    def has_target(self) -> bool:
        return self.target_position is not None

    @property
    def target_reached(self) -> bool:
        return self._target_reached

    @property
    def navigation_failed(self) -> bool:
        return self._navigation_failed

    @property
    def path_finished(self) -> bool:
        return bool(self.path) and self._path_index >= len(self._world_points)

    @property
    def current_waypoint(self) -> tuple[float, float] | None:
        if not self._world_points or self._path_index >= len(self._world_points):
            return None
        return self._world_points[self._path_index]

    @property
    def remaining_waypoints(self) -> tuple[tuple[float, float], ...]:
        if self._path_index >= len(self._world_points):
            return ()
        return self._world_points[self._path_index:]

    def _actor_position(self) -> tuple[float, float]:
        body = self.body
        if body is None:
            raise RuntimeError(
                "NavigationAgent2D must be a descendant of CharacterBody2D."
            )
        return body.world_position

    def _world_to_tile(self, x: float, y: float) -> tuple[int, int]:
        if self.map_node is not None:
            return self.map_node.world_to_tile(x, y)
        if self.navigation is None:
            raise RuntimeError("NavigationAgent2D is not configured.")
        return self.navigation.tilemap.world_to_tile(x, y)

    def _tile_to_world(self, x: int, y: int) -> tuple[float, float]:
        if self.map_node is not None:
            return self.map_node.tile_world_position(x, y)
        if self.navigation is None:
            raise RuntimeError("NavigationAgent2D is not configured.")
        return self.navigation.tilemap.tile_to_world(x, y)

    def request_path(self) -> NavigationPath | None:
        if self.target_position is None:
            self.clear_target()
            return None
        if not self._try_lazy_bind() or self.navigation is None:
            self._set_navigation_failed()
            return None

        start_x, start_y = self._actor_position()
        goal_x, goal_y = self.target_position
        start = self._world_to_tile(start_x, start_y)
        goal = self._world_to_tile(goal_x, goal_y)

        path = self.navigation.find_path(start, goal)
        self.path = path
        self._target_dirty = False
        self._repath_elapsed = 0.0
        self._last_navigation_revision = self.navigation.revision

        if path is None or not path.found:
            self._world_points = ()
            self._path_index = 0
            self._set_navigation_failed()
            return None

        self._navigation_failed = False
        self._world_points = tuple(self._tile_to_world(x, y) for x, y in path.tiles)

        # The first tile is normally the tile the body already occupies.
        self._path_index = 1 if len(self._world_points) > 1 else len(self._world_points)
        self._emit(self._path_changed_callbacks)
        self._advance_waypoints()
        self._check_target_reached()
        return path

    def invalidate_path(self, *, repath: bool = True) -> None:
        self.path = None
        self._world_points = ()
        self._path_index = 0
        self._target_dirty = bool(repath and self.target_position is not None)

    # ------------------------------------------------------------------
    # Steering
    # ------------------------------------------------------------------

    @property
    def desired_direction(self) -> tuple[float, float]:
        waypoint = self.current_waypoint
        if waypoint is None:
            return (0.0, 0.0)

        x, y = self._actor_position()
        dx = waypoint[0] - x
        dy = waypoint[1] - y
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            return (0.0, 0.0)
        return (dx / length, dy / length)

    def preferred_velocity(self, speed: float) -> tuple[float, float]:
        """Return raw path-following velocity before local avoidance."""
        speed = float(speed)
        if speed < 0.0:
            raise ValueError("speed must be greater than or equal to zero.")
        dx, dy = self.desired_direction
        return (dx * speed, dy * speed)

    def desired_velocity(self, speed: float) -> tuple[float, float]:
        """Return path velocity adjusted by local crowd avoidance."""
        speed = float(speed)
        if speed < 0.0:
            raise ValueError("speed must be greater than or equal to zero.")

        preferred = self.preferred_velocity(speed)
        if (
            not self.avoidance_enabled
            or self.map_node is None
            or speed <= 0.0
        ):
            return preferred

        self._sync_avoidance_agent()
        return self.map_node.avoidance_state.solve_velocity(
            self._avoidance_owner_id,
            preferred,
            max_speed=speed,
            neighbor_distance=self.avoidance_neighbor_distance,
            time_horizon=self.avoidance_time_horizon,
            strength=self.avoidance_strength,
        )

    def _sync_avoidance_agent(self) -> None:
        if self.map_node is None:
            return

        body = self.body
        if body is None:
            return

        position = body.world_position
        velocity = (
            float(body.velocity.x),
            float(body.velocity.y),
        )
        self.map_node.avoidance_state.register(
            self._avoidance_owner_id,
            position=position,
            velocity=velocity,
            radius=max(float(self.avoidance_radius), 0.0),
            enabled=bool(self.avoidance_enabled),
        )

    def _unregister_avoidance(self) -> None:
        if self.map_node is not None:
            self.map_node.avoidance_state.unregister(
                self._avoidance_owner_id
            )

    @property
    def distance_to_target(self) -> float:
        if self.target_position is None:
            return 0.0
        x, y = self._actor_position()
        return math.hypot(self.target_position[0] - x, self.target_position[1] - y)

    def _advance_waypoints(self) -> None:
        if not self._world_points:
            return
        x, y = self._actor_position()
        tolerance = max(float(self.waypoint_tolerance), 0.0)

        while self._path_index < len(self._world_points):
            wx, wy = self._world_points[self._path_index]
            if math.hypot(wx - x, wy - y) > tolerance:
                break
            self._path_index += 1

    def _check_target_reached(self) -> bool:
        if self.target_position is None or self._target_reached:
            return self._target_reached
        if self.distance_to_target > max(float(self.target_tolerance), 0.0):
            return False

        self._target_reached = True
        self._path_index = len(self._world_points)
        self._emit(self._target_reached_callbacks)
        return True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update(self, delta_time: float) -> None:
        if self.target_position is None:
            return
        if not self._try_lazy_bind():
            return

        self._sync_avoidance_agent()
        self._repath_elapsed += max(float(delta_time), 0.0)

        if self.navigation is not None and self.navigation.revision != self._last_navigation_revision:
            self._target_dirty = True

        if self._target_dirty:
            self.request_path()
        elif (
            self.auto_repath
            and self.repath_interval > 0.0
            and self._repath_elapsed >= self.repath_interval
            and self.navigation is not None
            and self.navigation.revision != self._last_navigation_revision
        ):
            self.request_path()

        self._advance_waypoints()
        self._check_target_reached()

    def destroy(self) -> None:
        self._unregister_avoidance()
        super().destroy()

    # ------------------------------------------------------------------
    # Callback API
    # ------------------------------------------------------------------

    @staticmethod
    def _connect(callbacks: list[AgentCallback], callback: AgentCallback) -> None:
        if callback not in callbacks:
            callbacks.append(callback)

    @staticmethod
    def _disconnect(callbacks: list[AgentCallback], callback: AgentCallback) -> None:
        try:
            callbacks.remove(callback)
        except ValueError:
            pass

    def connect_path_changed(self, callback: AgentCallback) -> None:
        self._connect(self._path_changed_callbacks, callback)

    def disconnect_path_changed(self, callback: AgentCallback) -> None:
        self._disconnect(self._path_changed_callbacks, callback)

    def connect_target_reached(self, callback: AgentCallback) -> None:
        self._connect(self._target_reached_callbacks, callback)

    def disconnect_target_reached(self, callback: AgentCallback) -> None:
        self._disconnect(self._target_reached_callbacks, callback)

    def connect_navigation_failed(self, callback: AgentCallback) -> None:
        self._connect(self._navigation_failed_callbacks, callback)

    def disconnect_navigation_failed(self, callback: AgentCallback) -> None:
        self._disconnect(self._navigation_failed_callbacks, callback)

    def _emit(self, callbacks: list[AgentCallback]) -> None:
        for callback in tuple(callbacks):
            callback(self)

    def _set_navigation_failed(self) -> None:
        if self._navigation_failed:
            return
        self._navigation_failed = True
        self._target_reached = False
        self._emit(self._navigation_failed_callbacks)
