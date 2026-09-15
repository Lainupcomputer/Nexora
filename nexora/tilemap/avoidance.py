from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True, frozen=True)
class AvoidanceAgentSnapshot:
    owner_id: int
    position: tuple[float, float]
    velocity: tuple[float, float]
    radius: float
    enabled: bool = True


class NavigationAvoidanceState:
    """Shared local-avoidance registry for one TileMapNode.

    The implementation is intentionally lightweight: agents publish their
    latest position/velocity and query a reciprocal steering correction.
    It does not alter the global A* path. It only adjusts the preferred
    velocity locally so multiple agents avoid occupying the same space.
    """

    def __init__(self) -> None:
        self._agents: dict[int, AvoidanceAgentSnapshot] = {}

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    def register(
        self,
        owner_id: int,
        *,
        position: tuple[float, float],
        velocity: tuple[float, float] = (0.0, 0.0),
        radius: float = 12.0,
        enabled: bool = True,
    ) -> None:
        radius = max(float(radius), 0.0)
        self._agents[int(owner_id)] = AvoidanceAgentSnapshot(
            owner_id=int(owner_id),
            position=(float(position[0]), float(position[1])),
            velocity=(float(velocity[0]), float(velocity[1])),
            radius=radius,
            enabled=bool(enabled),
        )

    def unregister(self, owner_id: int) -> None:
        self._agents.pop(int(owner_id), None)

    def clear(self) -> None:
        self._agents.clear()

    def snapshot(self, owner_id: int) -> AvoidanceAgentSnapshot | None:
        return self._agents.get(int(owner_id))

    def neighbors(
        self,
        owner_id: int,
        *,
        distance: float,
    ) -> tuple[AvoidanceAgentSnapshot, ...]:
        owner = self._agents.get(int(owner_id))
        if owner is None:
            return ()

        maximum = max(float(distance), 0.0)
        if maximum <= 0.0:
            return ()

        result: list[AvoidanceAgentSnapshot] = []
        ox, oy = owner.position

        for other_id, other in self._agents.items():
            if other_id == owner.owner_id or not other.enabled:
                continue

            dx = other.position[0] - ox
            dy = other.position[1] - oy
            if dx * dx + dy * dy <= maximum * maximum:
                result.append(other)

        result.sort(key=lambda item: item.owner_id)
        return tuple(result)

    def solve_velocity(
        self,
        owner_id: int,
        preferred_velocity: tuple[float, float],
        *,
        max_speed: float,
        neighbor_distance: float = 64.0,
        time_horizon: float = 0.75,
        strength: float = 1.0,
    ) -> tuple[float, float]:
        owner = self._agents.get(int(owner_id))
        vx = float(preferred_velocity[0])
        vy = float(preferred_velocity[1])
        max_speed = max(float(max_speed), 0.0)

        if owner is None or not owner.enabled or max_speed <= 0.0:
            return self._clamp(vx, vy, max_speed)

        strength = max(float(strength), 0.0)
        if strength <= 0.0:
            return self._clamp(vx, vy, max_speed)

        horizon = max(float(time_horizon), 0.0)
        correction_x = 0.0
        correction_y = 0.0
        px, py = owner.position

        for other in self.neighbors(
            owner.owner_id,
            distance=neighbor_distance,
        ):
            rx = px - other.position[0]
            ry = py - other.position[1]
            distance = math.hypot(rx, ry)
            combined_radius = max(owner.radius + other.radius, 1e-6)

            # Immediate separation when circles overlap or almost overlap.
            if distance < combined_radius:
                if distance <= 1e-6:
                    # Stable deterministic fallback. A shared sign with each
                    # agent's own travel direction makes head-on agents choose
                    # opposite world-space sides.
                    speed = math.hypot(vx, vy)
                    if speed > 1e-6:
                        nx = -vy / speed
                        ny = vx / speed
                    else:
                        nx, ny = (0.0, 1.0)
                else:
                    nx = rx / distance
                    ny = ry / distance

                penetration = (combined_radius - distance) / combined_radius
                push = max_speed * (0.5 + penetration) * strength
                correction_x += nx * push
                correction_y += ny * push
                continue

            # Predict closest approach using preferred self velocity and the
            # latest observed velocity of the neighbor.
            if horizon <= 0.0:
                continue

            relative_vx = vx - other.velocity[0]
            relative_vy = vy - other.velocity[1]
            relative_speed_sq = (
                relative_vx * relative_vx
                + relative_vy * relative_vy
            )
            if relative_speed_sq <= 1e-9:
                continue

            t = -(
                rx * relative_vx
                + ry * relative_vy
            ) / relative_speed_sq
            t = min(max(t, 0.0), horizon)

            future_x = rx + relative_vx * t
            future_y = ry + relative_vy * t
            future_distance = math.hypot(future_x, future_y)

            if future_distance >= combined_radius:
                continue

            preferred_speed = math.hypot(vx, vy)
            if preferred_speed > 1e-6:
                side_x = -vy / preferred_speed
                side_y = vx / preferred_speed
            else:
                # If standing still, steer away from the predicted overlap.
                if future_distance > 1e-6:
                    side_x = future_x / future_distance
                    side_y = future_y / future_distance
                else:
                    side_x, side_y = (0.0, 1.0)

            urgency = (
                1.0 - future_distance / combined_radius
            )
            time_weight = 1.0 - (t / horizon) if horizon > 1e-9 else 1.0
            push = max_speed * urgency * (0.5 + 0.5 * time_weight) * strength
            correction_x += side_x * push
            correction_y += side_y * push

        return self._clamp(
            vx + correction_x,
            vy + correction_y,
            max_speed,
        )

    @staticmethod
    def _clamp(x: float, y: float, max_speed: float) -> tuple[float, float]:
        if max_speed <= 0.0:
            return (0.0, 0.0)
        speed = math.hypot(x, y)
        if speed <= max_speed or speed <= 1e-9:
            return (float(x), float(y))
        scale = max_speed / speed
        return (float(x * scale), float(y * scale))
