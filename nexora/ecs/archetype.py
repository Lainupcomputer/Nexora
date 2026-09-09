from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(slots=True)
class Chunk:
    capacity: int
    component_types: tuple[type, ...]

    entities: list[int]
    components: dict[type, list]

    def __init__(
        self,
        capacity: int,
        component_types: tuple[type, ...],
    ):
        self.capacity = capacity
        self.component_types = component_types

        self.entities = []

        self.components = {
            component_type: []
            for component_type in component_types
        }

    @property
    def count(self) -> int:
        return len(self.entities)

    @property
    def full(self) -> bool:
        return self.count >= self.capacity

    def add(
        self,
        entity_id: int,
        component_values: dict[type, object],
    ) -> int:

        if self.full:
            raise RuntimeError(
                "Chunk is full."
            )

        index = len(self.entities)

        self.entities.append(entity_id)

        for component_type in self.component_types:
            self.components[component_type].append(
                component_values[component_type]
            )

        return index

    def remove(
        self,
        index: int,
    ) -> tuple[int, dict[type, object]]:

        last_index = self.count - 1

        removed_entity = self.entities[index]

        removed_components = {
            component_type:
                self.components[component_type][index]
            for component_type in self.component_types
        }

        if index != last_index:

            moved_entity = self.entities[last_index]

            self.entities[index] = moved_entity

            for component_type in self.component_types:
                values = self.components[component_type]

                values[index] = values[last_index]

        self.entities.pop()

        for component_type in self.component_types:
            self.components[component_type].pop()

        return removed_entity, removed_components

    def iter_rows(
        self,
        component_types: tuple[type, ...],
    ) -> Iterator[tuple]:

        requested = [
            self.components[component_type]
            for component_type in component_types
        ]

        for index, entity_id in enumerate(
            self.entities
        ):

            yield (
                entity_id,
                *(
                    values[index]
                    for values in requested
                ),
            )


class Archetype:

    def __init__(
        self,
        component_types: tuple[type, ...],
        chunk_capacity: int = 1024,
    ):

        self.component_types = tuple(
            sorted(
                component_types,
                key=lambda component: (
                    component.__module__,
                    component.__qualname__,
                ),
            )
        )

        self.chunk_capacity = chunk_capacity

        self.chunks: list[Chunk] = []

    def _new_chunk(self) -> Chunk:

        chunk = Chunk(
            capacity=self.chunk_capacity,
            component_types=self.component_types,
        )

        self.chunks.append(chunk)

        return chunk

    def add(
        self,
        entity_id: int,
        components: dict[type, object],
    ) -> tuple[Chunk, int]:

        if (
            not self.chunks
            or self.chunks[-1].full
        ):
            chunk = self._new_chunk()

        else:
            chunk = self.chunks[-1]

        index = chunk.add(
            entity_id,
            components,
        )

        return chunk, index

    def remove(
        self,
        chunk: Chunk,
        index: int,
    ):

        return chunk.remove(index)

    def query(
        self,
        component_types: tuple[type, ...],
    ):

        for chunk in self.chunks:

            yield from chunk.iter_rows(
                component_types
            )

    @property
    def entity_count(self) -> int:

        return sum(
            chunk.count
            for chunk in self.chunks
        )

    @property
    def chunk_count(self) -> int:

        return len(self.chunks)