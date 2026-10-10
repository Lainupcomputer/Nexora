from __future__ import annotations

from weakref import WeakSet


class ParticleSystem:
    """Runtime registry for particle emitters and aggregate debug metrics."""

    def __init__(self) -> None:
        self._emitters: WeakSet = WeakSet()
        self.enabled = True

    def register(self, emitter) -> None:
        self._emitters.add(emitter)

    def unregister(self, emitter) -> None:
        self._emitters.discard(emitter)

    @property
    def emitters(self):
        return tuple(self._emitters)

    @property
    def emitter_count(self) -> int:
        return len(self._emitters)

    @property
    def particle_count(self) -> int:
        return sum(len(emitter.particles) for emitter in tuple(self._emitters))

    def clear(self) -> None:
        for emitter in tuple(self._emitters):
            emitter.clear()

    def stop_all(self, *, clear: bool = False) -> None:
        for emitter in tuple(self._emitters):
            emitter.stop(clear=clear)
