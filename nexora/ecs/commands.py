from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CommandType(Enum):
    CREATE = "create"
    DESTROY = "destroy"
    ADD_COMPONENT = "add_component"
    REMOVE_COMPONENT = "remove_component"


@dataclass(slots=True)
class Command:
    type: CommandType
    entity_id: int | None = None
    component: Any = None
    component_type: type | None = None
    components: tuple[Any, ...] = ()


class CommandBuffer:
    """
    Thread-local ECS command buffer.

    Commands are recorded while systems execute and are applied later
    on the ECS/world thread. This prevents workers from modifying
    archetype storage while another worker is iterating it.
    """

    __slots__ = ("_commands",)

    def __init__(self) -> None:
        self._commands: list[Command] = []

    def create(self, *components: Any) -> None:
        self._commands.append(
            Command(
                type=CommandType.CREATE,
                components=tuple(components),
            )
        )

    def destroy(self, entity: int) -> None:
        self._commands.append(
            Command(
                type=CommandType.DESTROY,
                entity_id=int(entity),
            )
        )

    def add(self, entity: int, component: Any) -> None:
        self._commands.append(
            Command(
                type=CommandType.ADD_COMPONENT,
                entity_id=int(entity),
                component=component,
            )
        )

    def remove(self, entity: int, component_type: type) -> None:
        self._commands.append(
            Command(
                type=CommandType.REMOVE_COMPONENT,
                entity_id=int(entity),
                component_type=component_type,
            )
        )

    def clear(self) -> None:
        self._commands.clear()

    def __len__(self) -> int:
        return len(self._commands)

    def __bool__(self) -> bool:
        return bool(self._commands)

    def drain(self) -> list[Command]:
        commands = self._commands
        self._commands = []
        return commands