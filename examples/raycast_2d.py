from __future__ import annotations

import math
import time

import sdl3

from nexora.ecs.world import World
from nexora.input.input import InputManager
from nexora.nodes import (
    CollisionShape2D,
    Node,
    RayCast2D,
    StaticBody2D,
)
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.threading.context import ThreadContext
from nexora.debug.physics import PhysicsDebugRenderer


WIDTH = 1280
HEIGHT = 720

RAY_LENGTH = 420.0
MOVE_SPEED = 220.0


def create_wall(
    world: World,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> StaticBody2D:
    wall = StaticBody2D(
        name,
        world,
    )

    wall.transform.x = x
    wall.transform.y = y

    shape = CollisionShape2D(
        f"{name}Collision",
        world,
        width=width,
        height=height,
    )

    wall.add_child(
        shape
    )

    return wall


def main() -> None:
    print("=" * 60)
    print(" Nexora RayCast2D Mouse Example")
    print("=" * 60)
    print()
    print("Controls")
    print("-" * 60)
    print("WASD   Move ray origin")
    print("Mouse  Aim ray")
    print("F4     Toggle physics debug")
    print("ESC    Quit")
    print()

    ThreadContext.initialize()

    context = None
    renderer = None
    input_manager = None

    try:
        # ======================================================
        # GPU / Renderer
        # ======================================================

        context = GPUContext(
            WIDTH,
            HEIGHT,
            title="Nexora - RayCast2D Mouse Example",
            debug=True,
            vsync=True,
        )

        renderer = Renderer(
            context
        )

        # ======================================================
        # Input
        # ======================================================

        input_manager = InputManager()

        input_manager.initialize(
            context.window
        )

        # ======================================================
        # World / Tree
        # ======================================================

        world = World()

        root = Node(
            "Root",
            world,
        )

        # ======================================================
        # RayCast
        # ======================================================

        ray = RayCast2D(
            "InteractionRay",
            world,
            target_x=RAY_LENGTH,
            target_y=0.0,
        )

        ray.transform.x = -300.0
        ray.transform.y = 0.0

        root.add_child(
            ray
        )

        # ======================================================
        # Obstacles
        # ======================================================

        wall_a = create_wall(
            world,
            "WallA",
            120.0,
            -130.0,
            70.0,
            260.0,
        )

        wall_b = create_wall(
            world,
            "WallB",
            -120.0,
            180.0,
            340.0,
            60.0,
        )

        wall_c = create_wall(
            world,
            "WallC",
            -80.0,
            -260.0,
            300.0,
            60.0,
        )

        wall_d = create_wall(
            world,
            "WallD",
            340.0,
            80.0,
            100.0,
            100.0,
        )

        root.add_child(
            wall_a
        )

        root.add_child(
            wall_b
        )

        root.add_child(
            wall_c
        )

        root.add_child(
            wall_d
        )

        # ======================================================
        # Debug
        # ======================================================

        physics_debug = PhysicsDebugRenderer()

        physics_debug.visible = True

        # ======================================================
        # Timing
        # ======================================================

        previous_time = (
            time.perf_counter()
        )

        last_collider = None

        running = True

        # ======================================================
        # Loop
        # ======================================================

        while running:
            now = (
                time.perf_counter()
            )

            delta_time = (
                now
                - previous_time
            )

            previous_time = now

            delta_time = min(
                delta_time,
                0.05,
            )

            # ==================================================
            # Events
            # ==================================================

            events = list(
                context.poll_events()
            )

            input_manager.begin_frame(
                events
            )

            for event in events:
                if (
                    event.type
                    == sdl3.SDL_EVENT_QUIT
                ):
                    running = False

            if input_manager.key_pressed(
                "escape"
            ):
                running = False

            # ==================================================
            # Debug toggle
            # ==================================================

            if input_manager.key_pressed(
                "f4"
            ):
                visible = (
                    physics_debug.toggle()
                )

                print(
                    "Physics debug:",
                    "ON"
                    if visible
                    else "OFF",
                )

            # ==================================================
            # Move origin
            # ==================================================

            move_x = 0.0
            move_y = 0.0

            if input_manager.key_down(
                "a"
            ):
                move_x -= 1.0

            if input_manager.key_down(
                "d"
            ):
                move_x += 1.0

            if input_manager.key_down(
                "w"
            ):
                move_y -= 1.0

            if input_manager.key_down(
                "s"
            ):
                move_y += 1.0

            length = math.hypot(
                move_x,
                move_y,
            )

            if length > 0.0:
                move_x /= length
                move_y /= length

            ray.transform.x += (
                move_x
                * MOVE_SPEED
                * delta_time
            )

            ray.transform.y += (
                move_y
                * MOVE_SPEED
                * delta_time
            )

            # ==================================================
            # Mouse aim
            # ==================================================
            #
            # Important:
            # Nexora uses world coordinates with (0, 0) at the
            # center of the screen in the current renderer setup.
            #
            # Input mouse coordinates are window coordinates.
            # Convert:
            #
            #     window -> centered world
            # ==================================================

            mouse_x, mouse_y = (
                input_manager.mouse_position
            )

            mouse_world_x = (
                mouse_x
                - WIDTH * 0.5
            )

            mouse_world_y = (
                mouse_y
                - HEIGHT * 0.5
            )

            ray_x, ray_y = (
                ray.world_position
            )

            direction_x = (
                mouse_world_x
                - ray_x
            )

            direction_y = (
                mouse_world_y
                - ray_y
            )

            direction_length = math.hypot(
                direction_x,
                direction_y,
            )

            if direction_length > 0.0001:
                direction_x /= (
                    direction_length
                )

                direction_y /= (
                    direction_length
                )

                ray.set_target(
                    direction_x
                    * RAY_LENGTH,
                    direction_y
                    * RAY_LENGTH,
                )

            # ==================================================
            # Ray query
            # ==================================================

            hit = (
                ray.force_raycast_update()
            )

            collider = (
                ray.get_collider()
            )

            # Only print when target changes.
            if collider is not last_collider:
                last_collider = collider

                if collider is None:
                    print(
                        "RayCast: no collision"
                    )

                else:
                    print()
                    print(
                        "RayCast hit:",
                        collider.name,
                    )

                    print(
                        "  point:",
                        ray.get_collision_point(),
                    )

                    print(
                        "  normal:",
                        ray.get_collision_normal(),
                    )

                    print(
                        "  distance:",
                        ray.get_collision_distance(),
                    )

                    if hit is not None:
                        print(
                            "  fraction:",
                            hit.fraction,
                        )

            # ==================================================
            # Rendering
            # ==================================================

            if not renderer.begin_frame():
                input_manager.end_frame()
                continue

            try:
                # ==============================================
                # Optional visual objects
                # ==============================================

                for wall in (
                    wall_a,
                    wall_b,
                    wall_c,
                    wall_d,
                ):
                    shape = (
                        wall.primary_collision_shape
                    )

                    if shape is None:
                        continue

                    (
                        x,
                        y,
                        width,
                        height,
                    ) = (
                        shape.world_rect
                    )

                    renderer.rect(
                        x,
                        y,
                        width,
                        height,
                        color=(
                            0.30,
                            0.10,
                            0.10,
                            1.0,
                        ),
                        origin=(
                            0.0,
                            0.0,
                        ),
                    )

                # ==============================================
                # Ray origin marker
                # ==============================================

                ray_x, ray_y = (
                    ray.world_position
                )

                renderer.rect(
                    ray_x - 8.0,
                    ray_y - 8.0,
                    16.0,
                    16.0,
                    color=(
                        0.15,
                        0.65,
                        0.95,
                        1.0,
                    ),
                    origin=(
                        0.0,
                        0.0,
                    ),
                )

                # ==============================================
                # Mouse marker
                # ==============================================

                renderer.line(
                    mouse_world_x - 6.0,
                    mouse_world_y,
                    mouse_world_x + 6.0,
                    mouse_world_y,
                    width=1.0,
                    color=(
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                    ),
                )

                renderer.line(
                    mouse_world_x,
                    mouse_world_y - 6.0,
                    mouse_world_x,
                    mouse_world_y + 6.0,
                    width=1.0,
                    color=(
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                    ),
                )

                # ==============================================
                # Physics debug
                # ==============================================

                physics_debug.render(
                    renderer,
                    root,
                )

                if not renderer.end_frame():
                    running = False

            except Exception:
                context.cancel_frame()
                raise

            input_manager.end_frame()

            time.sleep(
                0.001
            )

    finally:
        print()
        print(
            "Cleaning up..."
        )

        if input_manager is not None:
            input_manager.stop_text_input()

        if renderer is not None:
            renderer.destroy()

        if context is not None:
            context.destroy()

        print(
            "Done."
        )


if __name__ == "__main__":
    main()