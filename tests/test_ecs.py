from nexora.ecs import (
    World,
    Transform,
    Velocity,
    Health,
    System,
)


class MovementSystem(System):

    def fixed_update(
        self,
        world,
        dt,
    ):

        for entity, transform, velocity in world.query(
            Transform,
            Velocity,
        ):

            transform.x += velocity.x * dt
            transform.y += velocity.y * dt


def main():

    print("=" * 60)
    print("NEXORA ECS TEST")
    print("=" * 60)

    world = World()

    movement = world.add_system(
        MovementSystem()
    )

    player = world.create_entity()

    world.add_component(
        player,
        Transform(
            x=100,
            y=200,
        ),
    )

    world.add_component(
        player,
        Velocity(
            x=60,
            y=30,
        ),
    )

    world.add_component(
        player,
        Health(
            current=100,
            maximum=100,
        ),
    )

    print()
    print(
        "Entity:",
        player.id,
    )

    print(
        "Entities:",
        world.entity_count(),
    )

    print()

    transform = world.get_component(
        player,
        Transform,
    )

    print(
        "Initial position:",
        transform.x,
        transform.y,
    )

    # Simulate one second at 60 Hz.
    for _ in range(60):

        world.fixed_update(
            1.0 / 60.0
        )

    print(
        "After 60 fixed updates:",
        transform.x,
        transform.y,
    )

    print()

    if abs(transform.x - 160.0) < 0.001:
        print(
            "Movement X: ✅"
        )
    else:
        print(
            "Movement X: ❌"
        )

    if abs(transform.y - 230.0) < 0.001:
        print(
            "Movement Y: ✅"
        )
    else:
        print(
            "Movement Y: ❌"
        )

    # Query test
    entities = list(
        world.query(
            Transform,
            Velocity,
        )
    )

    print(
        "Query results:",
        len(entities),
    )

    if len(entities) == 1:
        print(
            "Component query: ✅"
        )
    else:
        print(
            "Component query: ❌"
        )

    # Component test
    if world.has_component(
        player,
        Health,
    ):
        print(
            "Component storage: ✅"
        )

    # Destroy test
    world.destroy_entity(
        player
    )

    if not world.is_alive(player):
        print(
            "Entity destruction: ✅"
        )

    world.shutdown()

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print(
        "ECS test complete."
    )


if __name__ == "__main__":
    main()