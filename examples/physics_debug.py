from __future__ import annotations

import math
import time

import sdl3

from nexora.debug.physics import (
    PhysicsDebugRenderer,
)
from nexora.ecs.world import World
from nexora.input.input import InputManager
from nexora.nodes import (
    Area2D,
    CharacterBody2D,
    CollisionShape2D,
    Node,
    StaticBody2D,
)
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.threading.context import ThreadContext


# ==============================================================
# Configuration
# ==============================================================

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

PLAYER_SPEED = 220.0


# ==============================================================
# Player
# ==============================================================

def create_player(
    world: World,
) -> CharacterBody2D:
    player = CharacterBody2D(
        "Player",
        world,
    )

    player.transform.x = -450.0
    player.transform.y = -100.0

    collision = CollisionShape2D(
        "PlayerCollision",
        world,
        width=40.0,
        height=56.0,
    )

    player.add_child(
        collision
    )

    return player


# ==============================================================
# Walls
# ==============================================================

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

    collision = CollisionShape2D(
        f"{name}Collision",
        world,
        width=width,
        height=height,
    )

    wall.add_child(
        collision
    )

    return wall


# ==============================================================
# Area
# ==============================================================

def create_area(
    world: World,
) -> Area2D:
    area = Area2D(
        "TriggerArea",
        world,
    )

    area.transform.x = 250.0
    area.transform.y = -80.0

    collision = CollisionShape2D(
        "TriggerCollision",
        world,
        width=180.0,
        height=160.0,
    )

    area.add_child(
        collision
    )

    return area


# ==============================================================
# Visual helpers
# ==============================================================

def draw_body_rect(
    renderer: Renderer,
    body,
    *,
    color,
) -> None:
    shape = (
        body.primary_collision_shape
    )

    if shape is None:
        return

    x, y, width, height = (
        shape.world_rect
    )

    renderer.rect(
        x,
        y,
        width,
        height,
        color=color,
        origin=(
            0.0,
            0.0,
        ),
    )


def draw_grid(
    renderer: Renderer,
) -> None:
    """
    Simple world-space reference grid.
    """

    half_width = (
        renderer.width
        / 2.0
    )

    half_height = (
        renderer.height
        / 2.0
    )

    spacing = 64.0

    grid_color = (
        0.12,
        0.12,
        0.14,
        1.0,
    )

    x = (
        -half_width
        // spacing
        * spacing
    )

    while x <= half_width:
        renderer.line(
            x,
            -half_height,
            x,
            half_height,
            width=1.0,
            color=grid_color,
        )

        x += spacing

    y = (
        -half_height
        // spacing
        * spacing
    )

    while y <= half_height:
        renderer.line(
            -half_width,
            y,
            half_width,
            y,
            width=1.0,
            color=grid_color,
        )

        y += spacing


# ==============================================================
# Main
# ==============================================================

def main() -> None:
    print("=" * 60)
    print(" Nexora Physics Debug Example")
    print("=" * 60)
    print()
    print("Controls")
    print("-" * 60)
    print("W / A / S / D  Move player")
    print("F4             Toggle physics debug")
    print("ESC            Quit")
    print()

    # ==========================================================
    # Main-thread context
    # ==========================================================

    ThreadContext.initialize()

    context = None
    renderer = None
    input_manager = None

    try:
        # ======================================================
        # GPU
        # ======================================================

        print("Creating GPU context...")

        context = GPUContext(
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            title="Nexora - Physics Debug",
            debug=True,
            vsync=True,
        )

        print(
            f"GPU driver: "
            f"{context.driver}"
        )

        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )

        print()

        # ======================================================
        # Renderer
        # ======================================================

        print("Creating renderer...")

        renderer = Renderer(
            context
        )

        print()

        # ======================================================
        # Input
        # ======================================================

        print("Creating input manager...")

        input_manager = (
            InputManager()
        )

        input_manager.initialize(
            context.window,
        )

        print()

        # ======================================================
        # World / Node tree
        # ======================================================

        world = World()

        root = Node(
            "Root",
            world,
        )

        # ------------------------------------------------------
        # Player
        # ------------------------------------------------------

        player = create_player(
            world
        )

        root.add_child(
            player
        )

        # ------------------------------------------------------
        # Walls
        # ------------------------------------------------------

        wall_vertical = create_wall(
            world,
            "VerticalWall",
            -50.0,
            -180.0,
            70.0,
            360.0,
        )

        root.add_child(
            wall_vertical
        )

        wall_horizontal = create_wall(
            world,
            "HorizontalWall",
            20.0,
            130.0,
            330.0,
            60.0,
        )

        root.add_child(
            wall_horizontal
        )

        obstacle = create_wall(
            world,
            "Obstacle",
            -280.0,
            110.0,
            120.0,
            80.0,
        )

        root.add_child(
            obstacle
        )

        # ------------------------------------------------------
        # Trigger
        # ------------------------------------------------------

        area = create_area(
            world
        )

        root.add_child(
            area
        )

        # ======================================================
        # Area callbacks
        # ======================================================

        def on_area_entered(
            body,
        ) -> None:
            print(
                f"[AREA] entered -> "
                f"{body.name}"
            )

        def on_area_exited(
            body,
        ) -> None:
            print(
                f"[AREA] exited  -> "
                f"{body.name}"
            )

        area.connect_body_entered(
            on_area_entered
        )

        area.connect_body_exited(
            on_area_exited
        )

        # ======================================================
        # Physics Debug
        # ======================================================

        physics_debug = (
            PhysicsDebugRenderer()
        )

        # Start enabled so we immediately see whether it works.
        physics_debug.visible = True

        print(
            "Physics debug: ON"
        )

        print()
        print(
            "Starting example..."
        )
        print()

        # ======================================================
        # Loop
        # ======================================================

        running = True

        previous_time = (
            time.perf_counter()
        )

        while running:
            # ==================================================
            # Delta time
            # ==================================================

            current_time = (
                time.perf_counter()
            )

            delta_time = (
                current_time
                - previous_time
            )

            previous_time = (
                current_time
            )

            # Protect physics when debugging / moving the window.
            delta_time = min(
                delta_time,
                0.05,
            )

            # ==================================================
            # SDL events
            # ==================================================

            events = list(
                context.poll_events()
            )

            for event in events:
                if (
                    event.type
                    == sdl3.SDL_EVENT_QUIT
                ):
                    running = False

                elif (
                    event.type
                    == sdl3.SDL_EVENT_KEY_DOWN
                ):
                    if (
                        event.key.key
                        == sdl3.SDLK_ESCAPE
                    ):
                        running = False

            if not running:
                break

            # ==================================================
            # Input frame
            # ==================================================

            input_manager.begin_frame(
                events
            )

            # ==================================================
            # Physics debug toggle
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
            # Player movement
            # ==================================================

            movement_x = 0.0
            movement_y = 0.0

            if input_manager.key_down(
                "a"
            ):
                movement_x -= 1.0

            if input_manager.key_down(
                "d"
            ):
                movement_x += 1.0

            if input_manager.key_down(
                "w"
            ):
                movement_y -= 1.0

            if input_manager.key_down(
                "s"
            ):
                movement_y += 1.0

            # --------------------------------------------------
            # Normalize diagonal input
            # --------------------------------------------------

            length = math.sqrt(
                movement_x
                * movement_x
                + movement_y
                * movement_y
            )

            if length > 0.0:
                movement_x /= length
                movement_y /= length

            # --------------------------------------------------
            # Velocity
            # --------------------------------------------------

            player.velocity.set(
                movement_x
                * PLAYER_SPEED,
                movement_y
                * PLAYER_SPEED,
            )

            # --------------------------------------------------
            # Automatic Node-tree collision
            # --------------------------------------------------

            player.move_and_slide(
                delta_time
            )

            # ==================================================
            # Area monitoring
            # ==================================================

            area.update_overlaps()

            # ==================================================
            # Render frame
            # ==================================================

            if not renderer.begin_frame():
                input_manager.end_frame()

                time.sleep(
                    0.001
                )

                continue

            try:
                # ==============================================
                # Grid
                # ==============================================

                draw_grid(
                    renderer
                )

                # ==============================================
                # Trigger visual
                # ==============================================

                draw_body_rect(
                    renderer,
                    area,
                    color=(
                        0.08,
                        0.18,
                        0.30,
                        0.35,
                    ),
                )

                # ==============================================
                # Static bodies
                # ==============================================

                draw_body_rect(
                    renderer,
                    wall_vertical,
                    color=(
                        0.40,
                        0.12,
                        0.12,
                        1.0,
                    ),
                )

                draw_body_rect(
                    renderer,
                    wall_horizontal,
                    color=(
                        0.40,
                        0.12,
                        0.12,
                        1.0,
                    ),
                )

                draw_body_rect(
                    renderer,
                    obstacle,
                    color=(
                        0.40,
                        0.12,
                        0.12,
                        1.0,
                    ),
                )

                # ==============================================
                # Player
                # ==============================================

                draw_body_rect(
                    renderer,
                    player,
                    color=(
                        0.12,
                        0.55,
                        0.20,
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

                # ==============================================
                # Submit
                # ==============================================

                if not renderer.end_frame():
                    running = False

            except Exception:
                context.cancel_frame()
                raise

            # ==================================================
            # End input frame
            # ==================================================

            input_manager.end_frame()

            # Tiny yield so the example doesn't spin needlessly
            # when VSync is unavailable.
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