from __future__ import annotations
from nexora.ecs.commands import CommandBuffer, CommandType
from collections import defaultdict

from nexora.ecs.archetype import (
    Archetype,
    Chunk,
)
from nexora.ecs.entity import Entity
from nexora.ecs.parallel import ParallelChunkExecutor
from nexora.ecs.system import System
from nexora.ecs.scheduler import ECSSystemScheduler
from nexora.ecs.parallel import ParallelChunkExecutor
from nexora.ecs.scheduler import ECSSystemScheduler

class ArchetypeWorld:

    def __init__(self, chunk_capacity=1024, scheduler=None):
        if chunk_capacity <= 0:
            raise ValueError("chunk_capacity must be greater than 0.")
        self._command_buffers: dict[int, CommandBuffer] = {}
        self.chunk_capacity = chunk_capacity
        self._next_entity_id = 0
        self._alive = set()
        self._archetypes = {}
        self._locations = {}

        # Shared worker scheduler
        self.scheduler = scheduler

        # Parallel chunk execution
        self.parallel_executor = (
            ParallelChunkExecutor(scheduler)
            if scheduler is not None
            else None
        )

        # ECS dependency/system scheduler
        self.system_scheduler = ECSSystemScheduler(
            self,
            task_scheduler=scheduler,
        )
    # =========================================================
    # ARCHETYPES
    # =========================================================

    def _key(
        self,
        component_types,
    ) -> tuple[type, ...]:

        return tuple(
            sorted(
                component_types,
                key=lambda component: (
                    component.__module__,
                    component.__qualname__,
                ),
            )
        )

    def _get_archetype(
        self,
        component_types,
    ) -> Archetype:

        key = self._key(
            component_types
        )

        archetype = self._archetypes.get(key)

        if archetype is None:

            archetype = Archetype(
                component_types=key,
                chunk_capacity=self.chunk_capacity,
            )

            self._archetypes[key] = archetype

        return archetype

    # =========================================================
    # ENTITIES
    # =========================================================

    def create_entity(
        self,
        *components,
    ) -> Entity:

        entity = Entity(
            self._next_entity_id
        )

        self._next_entity_id += 1

        component_map = {
            type(component): component
            for component in components
        }

        archetype = self._get_archetype(
            component_map.keys()
        )

        chunk, index = archetype.add(
            entity.id,
            component_map,
        )

        self._alive.add(entity.id)

        self._locations[entity.id] = (
            archetype,
            chunk,
            index,
        )

        return entity

    def destroy_entity(
        self,
        entity: Entity,
    ) -> None:

        location = self._locations.pop(
            entity.id,
            None,
        )

        if location is None:
            return

        archetype, chunk, index = location

        removed_entity, _ = archetype.remove(
            chunk,
            index,
        )

        self._alive.discard(
            removed_entity
        )

        # The last entity was moved into the
        # removed slot.
        if index < chunk.count:

            moved_entity = chunk.entities[
                index
            ]

            self._locations[
                moved_entity
            ] = (
                archetype,
                chunk,
                index,
            )

    def is_alive(
        self,
        entity: Entity,
    ) -> bool:

        return entity.id in self._alive

    def entity_count(self) -> int:
        return len(self._alive)

    # =========================================================
    # COMPONENTS
    # =========================================================

    def add_component(
        self,
        entity: Entity,
        component,
    ):

        if not self.is_alive(entity):
            raise ValueError(
                f"Entity {entity.id} does not exist."
            )

        old_archetype, old_chunk, old_index = (
            self._locations[entity.id]
        )

        old_types = set(
            old_archetype.component_types
        )

        component_type = type(component)

        if component_type in old_types:

            old_chunk.components[
                component_type
            ][old_index] = component

            return component

        values = {
            component_type: old_chunk.components[
                component_type
            ][old_index]
            for component_type
            in old_archetype.component_types
        }

        values[component_type] = component

        old_archetype.remove(
            old_chunk,
            old_index,
        )

        new_archetype = self._get_archetype(
            values.keys()
        )

        new_chunk, new_index = (
            new_archetype.add(
                entity.id,
                values,
            )
        )

        self._locations[
            entity.id
        ] = (
            new_archetype,
            new_chunk,
            new_index,
        )

        if old_index < old_chunk.count:

            moved_entity = old_chunk.entities[
                old_index
            ]

            self._locations[
                moved_entity
            ] = (
                old_archetype,
                old_chunk,
                old_index,
            )

        return component

    def get_component(
        self,
        entity: Entity,
        component_type: type,
    ):

        location = self._locations.get(
            entity.id
        )

        if location is None:
            return None

        _, chunk, index = location

        values = chunk.components.get(
            component_type
        )

        if values is None:
            return None

        return values[index]

    def has_component(
        self,
        entity: Entity,
        component_type: type,
    ) -> bool:

        return (
            self.get_component(
                entity,
                component_type,
            )
            is not None
        )

    def remove_component(
        self,
        entity: Entity,
        component_type: type,
    ):

        location = self._locations.get(
            entity.id
        )

        if location is None:
            return None

        old_archetype, old_chunk, old_index = (
            location
        )

        if component_type not in (
            old_archetype.component_types
        ):
            return None

        if len(
            old_archetype.component_types
        ) == 1:

            removed = old_chunk.components[
                component_type
            ][old_index]

            self.destroy_entity(entity)

            return removed

        values = {
            component_type_: old_chunk.components[
                component_type_
            ][old_index]
            for component_type_
            in old_archetype.component_types
            if component_type_ != component_type
        }

        removed = old_chunk.components[
            component_type
        ][old_index]

        old_archetype.remove(
            old_chunk,
            old_index,
        )

        new_archetype = self._get_archetype(
            values.keys()
        )

        new_chunk, new_index = (
            new_archetype.add(
                entity.id,
                values,
            )
        )

        self._locations[
            entity.id
        ] = (
            new_archetype,
            new_chunk,
            new_index,
        )

        if old_index < old_chunk.count:

            moved_entity = old_chunk.entities[
                old_index
            ]

            self._locations[
                moved_entity
            ] = (
                old_archetype,
                old_chunk,
                old_index,
            )

        return removed

    # =========================================================
    # QUERY
    # =========================================================

    def query(
        self,
        *component_types: type,
    ):

        if not component_types:
            return

        required = set(
            component_types
        )

        for archetype in self._archetypes.values():

            if not required.issubset(
                archetype.component_types
            ):
                continue

            for row in archetype.query(
                tuple(component_types)
            ):

                entity_id = row[0]

                yield (
                    Entity(entity_id),
                    *row[1:],
                )

    # =========================================================
    # DEBUG
    # =========================================================

    def archetype_count(self) -> int:
        return len(self._archetypes)

    def chunk_count(self) -> int:

        return sum(
            archetype.chunk_count
            for archetype
            in self._archetypes.values()
        )

    def statistics(self) -> dict:

        return {
            "entities": self.entity_count(),
            "archetypes": self.archetype_count(),
            "chunks": self.chunk_count(),
            "chunk_capacity": self.chunk_capacity,
        }


    def parallel_query(
        self,
        component_types: tuple[type, ...],
        function,
    ) -> None:

        if self.parallel_executor is None:
            raise RuntimeError(
                "No TaskScheduler configured."
            )

        required = set(component_types)

        chunks = []

        for archetype in self._archetypes.values():

            if not required.issubset(
                archetype.component_types
            ):
                continue

            chunks.extend(archetype.chunks)

        if not chunks:
            return

        def process_chunks(chunk_group):

            for chunk in chunk_group:

                function(
                    chunk.entities,
                    *(
                        chunk.components[
                            component_type
                        ]
                        for component_type
                        in component_types
                    ),
                )

        self.parallel_executor.execute(
            chunks,
            process_chunks,
        )

    def add_system(
        self,
        system: System,
        *,
        reads=(),
        writes=(),
        priority: int = 0,
        main_thread_only: bool = False,
        depends_on=(),
    ):
        return self.system_scheduler.add_system(
            system,
            reads=reads,
            writes=writes,
            priority=priority,
            main_thread_only=main_thread_only,
            depends_on=depends_on,
        )

    def remove_system(self, system: System) -> None:
        self.system_scheduler.remove_system(system)

    def update(self, delta_time: float) -> None:
        self.system_scheduler.update(
            delta_time
        )

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:

        self.system_scheduler.fixed_update(
            fixed_delta_time
        )

    def render(
        self,
        interpolation: float,
    ) -> None:

        self.system_scheduler.render(
            interpolation
        )

    def shutdown(self) -> None:
        self.system_scheduler.shutdown()

    def create_command_buffer(self) -> CommandBuffer:
        """
        Create a command buffer for the current thread.
        """
        import threading

        thread_id = threading.get_ident()

        buffer = self._command_buffers.get(thread_id)

        if buffer is None:
            buffer = CommandBuffer()
            self._command_buffers[thread_id] = buffer

        return buffer

    def apply_commands(self) -> int:
        """
        Apply all recorded ECS commands.

        Must run after parallel system execution, when no worker is
        modifying or iterating the ECS storage.
        """

        commands: list = []

        for buffer in self._command_buffers.values():
            commands.extend(buffer.drain())

        applied = 0

        for command in commands:

            if command.type is CommandType.CREATE:
                self.create_entity(
                    *command.components
                )
                applied += 1

            elif command.type is CommandType.DESTROY:
                if command.entity_id is None:
                    continue

                entity = Entity(command.entity_id)

                if self.is_alive(entity):
                    self.destroy_entity(entity)
                    applied += 1

            elif command.type is CommandType.ADD_COMPONENT:
                if command.entity_id is None:
                    continue

                entity = Entity(command.entity_id)

                if (
                    self.is_alive(entity)
                    and command.component is not None
                ):
                    self.add_component(
                        entity,
                        command.component,
                    )
                    applied += 1

            elif command.type is CommandType.REMOVE_COMPONENT:
                if (
                    command.entity_id is None
                    or command.component_type is None
                ):
                    continue

                entity = Entity(command.entity_id)

                if self.is_alive(entity):
                    self.remove_component(
                        entity,
                        command.component_type,
                    )
                    applied += 1

        return applied

    def commands(self) -> CommandBuffer:
        return self.create_command_buffer()

    