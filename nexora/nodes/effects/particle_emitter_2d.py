from __future__ import annotations

from random import Random

from nexora.nodes.node import Node
from nexora.particles import Particle, ParticleConfig
from nexora.particles.modules import BurstModule


class ParticleEmitter2D(Node):
    """Configurable 2D particle emitter that can be attached anywhere in a Node tree."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.config = ParticleConfig()
        self.particles: list[Particle] = []
        self.emitting = False
        self.elapsed = 0.0
        self._emission_accumulator = 0.0
        self._cycle = 0
        self._fired_bursts: set[tuple[int, int]] = set()
        self._rng = Random()

        self.particle_emitted = self.create_signal("particle_emitted")
        self.finished = self.create_signal("finished")

    @property
    def particle_count(self) -> int:
        return len(self.particles)

    def set_seed(self, seed: int | None) -> None:
        self._rng.seed(seed)

    def play(self, *, restart: bool = False) -> None:
        if restart:
            self.restart()
            return
        self.emitting = True

    def stop(self, *, clear: bool = False) -> None:
        self.emitting = False
        if clear:
            self.clear()

    def restart(self) -> None:
        self.clear()
        self.elapsed = 0.0
        self._cycle = 0
        self._emission_accumulator = 0.0
        self._fired_bursts.clear()
        self.emitting = True
        self._process_bursts(0.0, 0.0)

    def clear(self) -> None:
        self.particles.clear()

    def emit(self, count: int = 1) -> int:
        available = max(int(self.config.max_particles) - len(self.particles), 0)
        count = min(max(int(count), 0), available)
        if count <= 0:
            return 0

        origin_x, origin_y = self.world_position
        for _ in range(count):
            particle = Particle()
            for module in self.config.modules:
                if not isinstance(module, BurstModule):
                    module.initialize(particle, self._rng)
            if not self.config.local_space:
                particle.x += origin_x
                particle.y += origin_y
            self.particles.append(particle)
            self.particle_emitted.emit(particle)
        return count

    def _process_bursts(self, previous: float, current: float) -> None:
        for module in self.config.modules:
            if not isinstance(module, BurstModule):
                continue
            for index, (at_time, count) in enumerate(module.bursts):
                key = (self._cycle, index)
                if key in self._fired_bursts:
                    continue
                if (previous <= at_time <= current) or (previous == current == at_time):
                    self.emit(count)
                    self._fired_bursts.add(key)

    def _advance_emission(self, delta_time: float) -> None:
        if not self.emitting:
            return

        duration = max(float(self.config.duration), 0.0)
        previous = self.elapsed
        self.elapsed += delta_time

        self._process_bursts(previous, self.elapsed)

        rate = max(float(self.config.emission_rate), 0.0)
        if rate > 0.0:
            self._emission_accumulator += delta_time * rate
            count = int(self._emission_accumulator)
            if count:
                self._emission_accumulator -= count
                self.emit(count)

        if duration <= 0.0 or self.elapsed < duration:
            return

        if self.config.looping and not self.config.one_shot:
            while duration > 0.0 and self.elapsed >= duration:
                self.elapsed -= duration
                self._cycle += 1
                self._fired_bursts.clear()
            self._process_bursts(0.0, self.elapsed)
        else:
            self.emitting = False
            if not self.particles:
                self.finished.emit()

    def update(self, delta_time: float) -> None:
        delta_time = max(float(delta_time), 0.0)
        self._advance_emission(delta_time)

        alive: list[Particle] = []
        for particle in self.particles:
            particle.age += delta_time
            if not particle.alive:
                continue
            for module in self.config.modules:
                if not isinstance(module, BurstModule):
                    module.update(particle, delta_time)
            particle.x += particle.vx * delta_time
            particle.y += particle.vy * delta_time
            alive.append(particle)

        had_particles = bool(self.particles)
        self.particles = alive
        if had_particles and not alive and not self.emitting:
            self.finished.emit()

    def render(self, renderer, interpolation: float) -> None:
        del interpolation
        if not self.particles:
            return

        origin_x, origin_y = self.world_position
        layer = int(self.config.layer)
        for particle in self.particles:
            if particle.size <= 0.0 or particle.color[3] <= 0.0:
                continue
            if self.config.local_space:
                x = origin_x + particle.x
                y = origin_y + particle.y
            else:
                x = particle.x
                y = particle.y
            renderer.circle(
                x,
                y,
                particle.size,
                color=particle.color,
                rotation=particle.rotation,
                layer=layer,
            )
