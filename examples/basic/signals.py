from __future__ import annotations

from nexora.ecs.world import World
from nexora.nodes import Node
from nexora.signals import EventBus


class Player(Node):
    def __init__(
        self,
        name: str,
        world: World,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.health = 100

        self.health_changed = (
            self.create_signal(
                "health_changed"
            )
        )

        self.died = (
            self.create_signal(
                "died"
            )
        )

    def damage(
        self,
        amount: int,
    ) -> None:
        self.health = max(
            0,
            self.health - amount,
        )

        self.health_changed.emit(
            self.health,
            100,
        )

        if self.health == 0:
            self.died.emit(self)


class HUD(Node):
    def on_health_changed(
        self,
        current: int,
        maximum: int,
    ) -> None:
        print(
            f"[HUD] Health: {current}/{maximum}"
        )


world = World()

player = Player(
    "Player",
    world,
)

hud = HUD(
    "HUD",
    world,
)

# Bound Node methods infer their owner automatically. Destroying HUD
# automatically disconnects this listener.
player.health_changed.connect(
    hud.on_health_changed
)

# One-shot callbacks are disconnected after their first call.
player.died.connect(
    lambda dead_player: print(
        f"{dead_player.name} died"
    ),
    once=True,
)

player.damage(25)
player.damage(25)

hud.destroy()

# No HUD output anymore because its connection was auto-disconnected.
player.damage(25)

# Named global events are available when sender and receiver should not
# know each other at all.
events = EventBus()

events.connect(
    "inventory.item_added",
    lambda item: print(
        f"Item added: {item}"
    ),
)

events.emit(
    "inventory.item_added",
    "Iron Ore",
)
