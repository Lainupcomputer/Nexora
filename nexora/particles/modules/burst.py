from __future__ import annotations

from dataclasses import dataclass

from .base import ParticleModule, register_module


@register_module
@dataclass(slots=True)
class BurstModule(ParticleModule):
    type_id = "burst"

    bursts: tuple[tuple[float, int], ...] = ((0.0, 10),)

    def to_state(self):
        return {
            "type": self.type_id,
            "bursts": tuple((float(t), int(count)) for t, count in self.bursts),
        }

    @classmethod
    def from_state(cls, state):
        return cls(tuple((float(t), int(count)) for t, count in state.get("bursts", ((0.0, 10),))))
