from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

from nexora.ecs.entity import Entity
from nexora.ecs.system import System


T = TypeVar("T")


class World:
    """
    Nexora ECS world.

    Stores entities, components and systems.
    """

    def __init__(self):

        self._next_entity_id = 0

        self._entities: set[int] = set()

        self._components: dict[
            type,
            dict[int, object],
        ] = defaultdict(dict)

        self._systems: list[System] = []

    # ---------------------------------------------------------
    # Entities
    # ---------------------------------------------------------

    def create_entity(self) -> Entity:

        entity = Entity(
            self._next_entity_id
        )

        self._next_entity_id += 1

        self._entities.add(entity.id)

        return entity

    def destroy_entity(
        self,
        entity: Entity,
    ) -> None:

        if entity.id not in self._entities:
            return

        self._entities.remove(entity.id)

        for storage in self._components.values():
            storage.pop(entity.id, None)

    def is_alive(
        self,
        entity: Entity,
    ) -> bool:

        return entity.id in self._entities

    def entity_count(self) -> int:
        return len(self._entities)

    # ---------------------------------------------------------
    # Components
    # ---------------------------------------------------------

    def add_component(
        self,
        entity: Entity,
        component: T,
    ) -> T:

        if not self.is_alive(entity):
            raise ValueError(
                f"Entity {entity.id} does not exist."
            )

        component_type = type(component)

        self._components[
            component_type
        ][entity.id] = component

        return component

    def remove_component(
        self,
        entity: Entity,
        component_type: type[T],
    ) -> T | None:

        storage = self._components.get(
            component_type
        )

        if storage is None:
            return None

        return storage.pop(
            entity.id,
            None,
        )

    def get_component(
        self,
        entity: Entity,
        component_type: type[T],
    ) -> T | None:

        storage = self._components.get(
            component_type
        )

        if storage is None:
            return None

        return storage.get(
            entity.id
        )

    def has_component(
        self,
        entity: Entity,
        component_type: type,
    ) -> bool:

        storage = self._components.get(
            component_type
        )

        if storage is None:
            return False

        return entity.id in storage

    # ---------------------------------------------------------
    # Query
    # ---------------------------------------------------------

    def query(
        self,
        *component_types: type,
    ):
        """
        Iterate over entities containing all requested
        component types.

        Example:

            for entity, transform, velocity in world.query(
                Transform,
                Velocity,
            ):
                ...
        """

        if not component_types:
            return

        storages = [
            self._components.get(
                component_type,
                {},
            )
            for component_type in component_types
        ]

        # Start with the smallest component storage.
        smallest_index = min(
            range(len(storages)),
            key=lambda index: len(storages[index]),
        )

        smallest_storage = storages[
            smallest_index
        ]

        for entity_id in tuple(
            smallest_storage.keys()
        ):

            if entity_id not in self._entities:
                continue

            components = []

            valid = True

            for storage in storages:

                component = storage.get(
                    entity_id
                )

                if component is None:
                    valid = False
                    break

                components.append(
                    component
                )

            if not valid:
                continue

            yield (
                Entity(entity_id),
                *components,
            )

    # ---------------------------------------------------------
    # Systems
    # ---------------------------------------------------------

    def add_system(
        self,
        system: System,
    ) -> System:

        self._systems.append(system)

        system.initialize(self)

        return system

    def remove_system(
        self,
        system: System,
    ) -> None:

        if system not in self._systems:
            return

        system.shutdown(self)

        self._systems.remove(system)

    def update(
        self,
        delta_time: float,
    ) -> None:

        for system in self._systems:

            if not system.enabled:
                continue

            system.update(
                self,
                delta_time,
            )

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:

        for system in self._systems:

            if not system.enabled:
                continue

            system.fixed_update(
                self,
                fixed_delta_time,
            )

    def render(
        self,
        interpolation: float,
    ) -> None:

        for system in self._systems:

            if not system.enabled:
                continue

            system.render(
                self,
                interpolation,
            )

    def shutdown(self) -> None:

        for system in reversed(
            self._systems
        ):
            system.shutdown(self)

        self._systems.clear()