from __future__ import annotations

from abc import ABC


class System(ABC):
    """
    Base class for all Nexora ECS systems.

    Systems are intentionally lightweight.
    Scheduling information is supplied when the system is registered
    with ECSSystemScheduler.
    """

    enabled: bool = True

    def initialize(self, world) -> None:
        pass

    def update(self, world, delta_time: float) -> None:
        pass

    def fixed_update(self, world, fixed_delta_time: float) -> None:
        pass

    def render(self, world, interpolation: float) -> None:
        pass

    def shutdown(self, world) -> None:
        pass