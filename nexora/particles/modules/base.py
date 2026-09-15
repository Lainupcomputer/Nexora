from __future__ import annotations

from abc import ABC
from random import Random
from typing import Any

from nexora.particles.particle import Particle


class ParticleModule(ABC):
    """Base class for serializable particle modules."""

    type_id = "module"

    def initialize(self, particle: Particle, rng: Random) -> None:
        del particle, rng

    def update(self, particle: Particle, delta_time: float) -> None:
        del particle, delta_time

    def to_state(self) -> dict[str, Any]:
        return {"type": self.type_id}


_MODULE_TYPES: dict[str, type[ParticleModule]] = {}


def register_module(cls: type[ParticleModule]) -> type[ParticleModule]:
    type_id = str(cls.type_id).strip()
    if not type_id:
        raise ValueError("Particle module type_id cannot be empty")
    _MODULE_TYPES[type_id] = cls
    return cls


def module_from_state(state: dict[str, Any]) -> ParticleModule:
    type_id = str(state.get("type", ""))
    cls = _MODULE_TYPES.get(type_id)
    if cls is None:
        raise ValueError(f"Unknown particle module type: {type_id!r}")
    factory = getattr(cls, "from_state", None)
    if factory is None:
        raise TypeError(f"Particle module {type_id!r} has no from_state()")
    return factory(dict(state))
