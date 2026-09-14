from __future__ import annotations

"""
Nexora Arena Survivor Prototype

Controls
--------
W / A / S / D  Move
ESC            Quit

This intentionally uses simple rectangles before final sprites, UI, and
game content are added. It is a small, playable reference for Nexora's
input, rendering, time, and future ECS gameplay workflow.
"""

from dataclasses import dataclass
import math
import random
import time

import sdl3

from nexora.input.input import InputManager
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.renderer import Renderer
from nexora.threading.context import ThreadContext


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

PLAYER_SPEED = 260.0
PLAYER_SIZE = 30.0
ENEMY_SIZE = 22.0
PROJECTILE_SIZE = 10.0
XP_SIZE = 12.0

RUN_DURATION = 300.0
START_SPAWN_INTERVAL = 1.15
MIN_SPAWN_INTERVAL = 0.12


@dataclass(slots=True)
class Player:
    x: float = 0.0
    y: float = 0.0
    health: float = 100.0
    max_health: float = 100.0
    experience: int = 0
    experience_to_level: int = 20
    level: int = 1
    kills: int = 0
    attack_timer: float = 0.0
    attack_interval: float = 0.55
    damage: float = 20.0
    projectile_speed: float = 560.0
    pickup_radius: float = 72.0


@dataclass(slots=True)
class Enemy:
    x: float
    y: float
    speed: float
    health: float
    damage: float
    attack_cooldown: float
    attack_timer: float
    color: tuple[float, float, float, float]


@dataclass(slots=True)
class Projectile:
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    damage: float
    lifetime: float = 1.4


@dataclass(slots=True)
class ExperienceOrb:
    x: float
    y: float
    value: int


class ArenaSurvivor:
    def __init__(self) -> None:
        self.player = Player()
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.experience_orbs: list[ExperienceOrb] = []

        self.run_time = 0.0
        self.spawn_timer = 0.35
        self.spawn_interval = START_SPAWN_INTERVAL
        self.finished = False

    def update(
        self,
        delta_time: float,
        input_manager: InputManager,
    ) -> None:
        if self.finished:
            return

        self.run_time += delta_time
        self._update_player(delta_time, input_manager)
        self._update_spawning(delta_time)
        self._update_auto_attack(delta_time)
        self._update_enemies(delta_time)
        self._update_projectiles(delta_time)
        self._update_experience(delta_time)
        self._check_run_state()

    def _update_player(
        self,
        delta_time: float,
        input_manager: InputManager,
    ) -> None:
        move_x = 0.0
        move_y = 0.0

        if input_manager.key_down("a"):
            move_x -= 1.0
        if input_manager.key_down("d"):
            move_x += 1.0
        if input_manager.key_down("w"):
            move_y -= 1.0
        if input_manager.key_down("s"):
            move_y += 1.0

        length = math.hypot(move_x, move_y)
        if length <= 0.0:
            return

        self.player.x += (
            move_x / length
            * PLAYER_SPEED
            * delta_time
        )
        self.player.y += (
            move_y / length
            * PLAYER_SPEED
            * delta_time
        )

    def _update_spawning(
        self,
        delta_time: float,
    ) -> None:
        self.spawn_timer -= delta_time

        difficulty = min(
            self.run_time / RUN_DURATION,
            1.0,
        )

        self.spawn_interval = max(
            MIN_SPAWN_INTERVAL,
            START_SPAWN_INTERVAL
            - difficulty * 1.0,
        )

        while self.spawn_timer <= 0.0:
            self.spawn_timer += self.spawn_interval
            self._spawn_enemy(difficulty)

    def _spawn_enemy(
        self,
        difficulty: float,
    ) -> None:
        angle = random.random() * math.tau
        distance = random.uniform(
            480.0,
            760.0,
        )

        health = 28.0 + difficulty * 54.0
        speed = 54.0 + difficulty * 52.0

        self.enemies.append(
            Enemy(
                x=self.player.x + math.cos(angle) * distance,
                y=self.player.y + math.sin(angle) * distance,
                speed=speed,
                health=health,
                damage=8.0 + difficulty * 7.0,
                attack_cooldown=0.7,
                attack_timer=random.uniform(
                    0.0,
                    0.7,
                ),
                color=(
                    0.84,
                    0.20 + difficulty * 0.20,
                    0.27,
                    1.0,
                ),
            )
        )

    def _update_auto_attack(
        self,
        delta_time: float,
    ) -> None:
        self.player.attack_timer -= delta_time
        if self.player.attack_timer > 0.0:
            return

        target = self._nearest_enemy()
        if target is None:
            return

        distance_x = target.x - self.player.x
        distance_y = target.y - self.player.y
        length = math.hypot(distance_x, distance_y)

        if length <= 0.001:
            return

        self.player.attack_timer = (
            self.player.attack_interval
        )

        self.projectiles.append(
            Projectile(
                x=self.player.x,
                y=self.player.y,
                velocity_x=(
                    distance_x / length
                    * self.player.projectile_speed
                ),
                velocity_y=(
                    distance_y / length
                    * self.player.projectile_speed
                ),
                damage=self.player.damage,
            )
        )

    def _nearest_enemy(self) -> Enemy | None:
        nearest: Enemy | None = None
        nearest_distance_squared = float("inf")

        for enemy in self.enemies:
            distance_x = enemy.x - self.player.x
            distance_y = enemy.y - self.player.y
            distance_squared = (
                distance_x * distance_x
                + distance_y * distance_y
            )

            if distance_squared < nearest_distance_squared:
                nearest = enemy
                nearest_distance_squared = distance_squared

        return nearest

    def _update_enemies(
        self,
        delta_time: float,
    ) -> None:
        alive: list[Enemy] = []

        for enemy in self.enemies:
            distance_x = self.player.x - enemy.x
            distance_y = self.player.y - enemy.y
            distance = math.hypot(distance_x, distance_y)

            if distance > 0.001:
                enemy.x += (
                    distance_x / distance
                    * enemy.speed
                    * delta_time
                )
                enemy.y += (
                    distance_y / distance
                    * enemy.speed
                    * delta_time
                )

            enemy.attack_timer -= delta_time

            if (
                distance <= (
                    PLAYER_SIZE * 0.5
                    + ENEMY_SIZE * 0.5
                )
                and enemy.attack_timer <= 0.0
            ):
                self.player.health -= enemy.damage
                enemy.attack_timer = (
                    enemy.attack_cooldown
                )

            if enemy.health > 0.0:
                alive.append(enemy)
            else:
                self.player.kills += 1
                self.experience_orbs.append(
                    ExperienceOrb(
                        x=enemy.x,
                        y=enemy.y,
                        value=1,
                    )
                )

        self.enemies = alive

    def _update_projectiles(
        self,
        delta_time: float,
    ) -> None:
        active: list[Projectile] = []

        for projectile in self.projectiles:
            projectile.x += (
                projectile.velocity_x
                * delta_time
            )
            projectile.y += (
                projectile.velocity_y
                * delta_time
            )
            projectile.lifetime -= delta_time

            hit = False

            for enemy in self.enemies:
                if (
                    math.hypot(
                        enemy.x - projectile.x,
                        enemy.y - projectile.y,
                    )
                    <= (
                        ENEMY_SIZE * 0.5
                        + PROJECTILE_SIZE * 0.5
                    )
                ):
                    enemy.health -= projectile.damage
                    hit = True
                    break

            if (
                not hit
                and projectile.lifetime > 0.0
            ):
                active.append(projectile)

        self.projectiles = active

    def _update_experience(
        self,
        delta_time: float,
    ) -> None:
        remaining: list[ExperienceOrb] = []

        for orb in self.experience_orbs:
            distance_x = self.player.x - orb.x
            distance_y = self.player.y - orb.y
            distance = math.hypot(distance_x, distance_y)

            if distance <= self.player.pickup_radius:
                if distance > 0.001:
                    pull_speed = max(
                        260.0,
                        820.0
                        * (
                            1.0
                            - distance
                            / self.player.pickup_radius
                        ),
                    )
                    orb.x += (
                        distance_x / distance
                        * pull_speed
                        * delta_time
                    )
                    orb.y += (
                        distance_y / distance
                        * pull_speed
                        * delta_time
                    )

                if distance <= XP_SIZE:
                    self._gain_experience(orb.value)
                    continue

            remaining.append(orb)

        self.experience_orbs = remaining

    def _gain_experience(
        self,
        amount: int,
    ) -> None:
        self.player.experience += amount

        while (
            self.player.experience
            >= self.player.experience_to_level
        ):
            self.player.experience -= (
                self.player.experience_to_level
            )
            self.player.level += 1
            self.player.experience_to_level = int(
                self.player.experience_to_level
                * 1.35
            )
            self._apply_random_upgrade()

            print(
                f"[LEVEL UP] Level {self.player.level} | "
                f"Damage {self.player.damage:.0f} | "
                f"Attack {self.player.attack_interval:.2f}s"
            )

    def _apply_random_upgrade(
        self,
    ) -> None:
        upgrade = random.choice(
            (
                "damage",
                "attack_speed",
                "health",
                "pickup",
                "projectile_speed",
            )
        )

        if upgrade == "damage":
            self.player.damage += 7.0
        elif upgrade == "attack_speed":
            self.player.attack_interval = max(
                0.16,
                self.player.attack_interval - 0.07,
            )
        elif upgrade == "health":
            self.player.max_health += 18.0
            self.player.health = min(
                self.player.max_health,
                self.player.health + 24.0,
            )
        elif upgrade == "pickup":
            self.player.pickup_radius += 18.0
        else:
            self.player.projectile_speed += 85.0

    def _check_run_state(
        self,
    ) -> None:
        if self.player.health <= 0.0:
            self.finished = True
            print(
                f"[GAME OVER] {self.run_time:.1f}s | "
                f"Level {self.player.level} | "
                f"Kills {self.player.kills}"
            )
        elif self.run_time >= RUN_DURATION:
            self.finished = True
            print(
                f"[RUN COMPLETE] {self.player.kills} kills"
            )

    def render(
        self,
        renderer: Renderer,
    ) -> None:
        # Camera follows the player by converting world positions
        # into Nexora's center-origin screen space.
        for orb in self.experience_orbs:
            self._draw_rect(
                renderer,
                orb.x,
                orb.y,
                XP_SIZE,
                XP_SIZE,
                (0.20, 0.82, 0.95, 1.0),
            )

        for enemy in self.enemies:
            self._draw_rect(
                renderer,
                enemy.x,
                enemy.y,
                ENEMY_SIZE,
                ENEMY_SIZE,
                enemy.color,
            )

        for projectile in self.projectiles:
            self._draw_rect(
                renderer,
                projectile.x,
                projectile.y,
                PROJECTILE_SIZE,
                PROJECTILE_SIZE,
                (1.0, 0.86, 0.28, 1.0),
            )

        self._draw_rect(
            renderer,
            self.player.x,
            self.player.y,
            PLAYER_SIZE,
            PLAYER_SIZE,
            (0.24, 0.75, 0.42, 1.0),
        )

        self._render_hud(renderer)

    def _draw_rect(
        self,
        renderer: Renderer,
        world_x: float,
        world_y: float,
        width: float,
        height: float,
        color: tuple[float, float, float, float],
    ) -> None:
        renderer.rect(
            world_x - self.player.x,
            world_y - self.player.y,
            width,
            height,
            color=color,
            origin=(0.5, 0.5),
        )

    def _render_hud(
        self,
        renderer: Renderer,
    ) -> None:
        bar_x = -560.0
        bar_y = -320.0
        bar_width = 280.0
        bar_height = 18.0

        health_ratio = max(
            0.0,
            self.player.health
            / self.player.max_health,
        )
        experience_ratio = (
            self.player.experience
            / self.player.experience_to_level
        )

        renderer.rect(
            bar_x,
            bar_y,
            bar_width,
            bar_height,
            color=(0.08, 0.08, 0.10, 0.9),
            origin=(0.0, 0.0),
        )
        renderer.rect(
            bar_x,
            bar_y,
            bar_width * health_ratio,
            bar_height,
            color=(0.82, 0.20, 0.26, 1.0),
            origin=(0.0, 0.0),
        )
        renderer.rect(
            bar_x,
            bar_y + 28.0,
            bar_width,
            10.0,
            color=(0.08, 0.08, 0.10, 0.9),
            origin=(0.0, 0.0),
        )
        renderer.rect(
            bar_x,
            bar_y + 28.0,
            bar_width * experience_ratio,
            10.0,
            color=(0.24, 0.52, 1.0, 1.0),
            origin=(0.0, 0.0),
        )


def main() -> None:
    print("=" * 56)
    print(" Nexora Arena Survivor Prototype")
    print("=" * 56)
    print("W / A / S / D : move")
    print("ESC           : quit")
    print("Survive for five minutes.")
    print()

    ThreadContext.initialize()

    context: GPUContext | None = None
    renderer: Renderer | None = None
    input_manager: InputManager | None = None

    try:
        context = GPUContext(
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            title="Nexora - Arena Survivor Prototype",
            debug=True,
            vsync=True,
        )
        renderer = Renderer(context)

        input_manager = InputManager()
        input_manager.initialize(context.window)

        game = ArenaSurvivor()
        running = True
        previous_time = time.perf_counter()

        while running:
            current_time = time.perf_counter()
            delta_time = min(
                current_time - previous_time,
                0.05,
            )
            previous_time = current_time

            events = list(context.poll_events())

            for event in events:
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False
                elif (
                    event.type
                    == sdl3.SDL_EVENT_KEY_DOWN
                    and event.key.key
                    == sdl3.SDLK_ESCAPE
                ):
                    running = False

            if not running:
                break

            input_manager.begin_frame(events)
            game.update(delta_time, input_manager)

            if renderer.begin_frame():
                try:
                    game.render(renderer)
                    renderer.end_frame()
                except Exception:
                    context.cancel_frame()
                    raise

            input_manager.end_frame()
            time.sleep(0.001)

    finally:
        if input_manager is not None:
            input_manager.stop_text_input()

        if renderer is not None:
            renderer.destroy()

        if context is not None:
            context.destroy()


if __name__ == "__main__":
    main()
