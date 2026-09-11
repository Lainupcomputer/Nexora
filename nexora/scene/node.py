from __future__ import annotations
import math
from typing import TYPE_CHECKING

from nexora.ecs.entity import Entity
from nexora.ecs.component import Transform

if TYPE_CHECKING:
    from nexora.ecs.world import World


class Node:
    """A hierarchical scene node backed by an ECS entity."""

    def __init__(
        self,
        name: str,
        world: World,
    ) -> None:
        self.name = name
        self.world = world

        self.entity: Entity = world.create_entity()

        self.transform = world.add_component(
            self.entity,
            Transform(),
        )

        self.parent: Node | None = None
        self.children: list[Node] = []

    @property
    def world_position(self) -> tuple[float, float]:
        x = self.transform.x
        y = self.transform.y

        if self.parent is None:
            return x, y

        parent_x, parent_y = self.parent.world_position

        angle = math.radians(self.parent.transform.rotation)
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)

        rotated_x = x * cos_angle - y * sin_angle
        rotated_y = x * sin_angle + y * cos_angle

        return (
            parent_x + rotated_x * self.parent.transform.scale_x,
            parent_y + rotated_y * self.parent.transform.scale_y,
        )

    @property
    def world_rotation(self) -> float:
        if self.parent is None:
            return self.transform.rotation

        return self.parent.world_rotation + self.transform.rotation

    @property
    def world_scale(self) -> tuple[float, float]:
        if self.parent is None:
            return (
                self.transform.scale_x,
                self.transform.scale_y,
            )

        parent_scale_x, parent_scale_y = self.parent.world_scale

        return (
            parent_scale_x * self.transform.scale_x,
            parent_scale_y * self.transform.scale_y,
        )

    @property
    def world_transform(self) -> Transform:
        x, y = self.world_position

        return Transform(
            x=x,
            y=y,
            rotation=self.world_rotation,
            scale_x=self.world_scale[0],
            scale_y=self.world_scale[1],
        )

    def add_child(self, child: Node) -> None:
        if child is self:
            raise ValueError("A node cannot be its own child.")

        if child.parent is self:
            return

        if child.parent is not None:
            child.parent.remove_child(child)

        child.parent = self
        self.children.append(child)

    def remove_child(self, child: Node) -> None:
        if child not in self.children:
            return

        self.children.remove(child)
        child.parent = None

    def find_child(self, name: str) -> Node | None:
        for child in self.children:
            if child.name == name:
                return child

            result = child.find_child(name)
            if result is not None:
                return result

        return None

    def destroy(self) -> None:
        for child in tuple(self.children):
            child.destroy()

        self.children.clear()

        if self.parent is not None:
            self.parent.remove_child(self)

        if self.world.is_alive(self.entity):
            self.world.destroy_entity(self.entity)