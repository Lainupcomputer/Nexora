from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .modules import ParticleModule, module_from_state


@dataclass(slots=True)
class ParticleConfig:
    max_particles: int = 256
    emission_rate: float = 20.0
    duration: float = 1.0
    looping: bool = True
    one_shot: bool = False
    local_space: bool = True
    layer: int = 0
    modules: list[ParticleModule] = field(default_factory=list)

    def add_module(self, module: ParticleModule) -> ParticleModule:
        self.modules.append(module)
        return module

    def get_module(self, module_type):
        for module in self.modules:
            if isinstance(module, module_type):
                return module
        return None

    def remove_modules(self, module_type) -> int:
        before = len(self.modules)
        self.modules[:] = [m for m in self.modules if not isinstance(m, module_type)]
        return before - len(self.modules)

    def to_state(self) -> dict[str, Any]:
        return {
            "max_particles": int(self.max_particles),
            "emission_rate": float(self.emission_rate),
            "duration": float(self.duration),
            "looping": bool(self.looping),
            "one_shot": bool(self.one_shot),
            "local_space": bool(self.local_space),
            "layer": int(self.layer),
            "modules": [module.to_state() for module in self.modules],
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "ParticleConfig":
        config = cls(
            max_particles=max(int(state.get("max_particles", 256)), 0),
            emission_rate=max(float(state.get("emission_rate", 20.0)), 0.0),
            duration=max(float(state.get("duration", 1.0)), 0.0),
            looping=bool(state.get("looping", True)),
            one_shot=bool(state.get("one_shot", False)),
            local_space=bool(state.get("local_space", True)),
            layer=int(state.get("layer", 0)),
        )
        config.modules = [module_from_state(dict(item)) for item in state.get("modules", [])]
        return config
