from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Callable, Mapping
from typing import Any

from nexora.animation import AnimationStateMachine
from nexora.nodes.entity.character_body_2d import CharacterBody2D
from nexora.state_machine import State, StateMachine


@dataclass(slots=True)
class AttackProfile:
    """Configuration for one weapon or tool attack."""

    name: str
    animation: str | None = None
    duration: float = 0.35
    sound: Any = None
    damage: float = 0.0


class _ControllerState(State):
    def __init__(self, controller: CharacterController2D, name: str) -> None:
        super().__init__(name)
        self.controller = controller

    def enter(self, previous: State | None, payload: Any = None) -> None:
        self.controller._on_state_enter(self.name, payload)

    def exit(self, next_state: State | None) -> None:
        self.controller._on_state_exit(self.name, next_state.name if next_state else None)

    def update(self, delta_time: float) -> None:
        self.controller._update_controller_state(self.name, delta_time)


class CharacterController2D(CharacterBody2D):
    """Binding-driven 2D character controller built on Nexora nodes.

    Add an ``AnimatedSprite`` or ``AnimationPlayer`` as a child and pass it to
    :meth:`set_animation_driver`. Animation names use the following convention::

        idle_south, walk_south, run_south, roll_south
        get_hit_south, get_critical_hit_south
        injured_south, heavily_injured_south

    The eight direction suffixes are ``north``, ``north_east``, ``east``,
    ``south_east``, ``south``, ``south_west``, ``west`` and ``north_west``.
    Missing clips are ignored, which makes it possible to provide only the
    animations a character actually owns.
    """

    DIRECTIONS = (
        "north", "north_east", "east", "south_east",
        "south", "south_west", "west", "north_west",
    )
    _DIRECTION_ABBREVIATIONS = {
        "north": "n", "north_east": "ne", "east": "e", "south_east": "se",
        "south": "s", "south_west": "sw", "west": "w", "north_west": "nw",
    }
    _STATES = (
        "idle", "walk", "run", "roll", "attack", "get_hit",
        "get_critical_hit", "injured", "heavily_injured", "dead",
    )
    _TRANSIENT_STATES = {
        "roll", "attack", "get_hit", "get_critical_hit", "injured", "heavily_injured",
    }

    DEFAULT_ACTIONS = {
        "up": "move_up",
        "down": "move_down",
        "left": "move_left",
        "right": "move_right",
        "run": "run",
        "roll": "roll",
        "attack": "attack",
    }
    DEFAULT_BINDINGS = {
        "move_up": "W", "move_down": "S", "move_left": "A", "move_right": "D",
        "run": "LSHIFT", "roll": "SPACE",
    }

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        # Movement tuning. Speeds are world units per second; friction and
        # acceleration are deceleration/acceleration units per second.
        self.walk_speed = 120.0
        self.run_speed = 200.0
        self.acceleration = 900.0
        self.friction = 1100.0
        self.roll_speed = 280.0
        self.roll_duration = 0.32
        self.roll_cooldown = 0.45

        self.input = None
        self.input_actions = dict(self.DEFAULT_ACTIONS)
        self.input_vector = (0.0, 0.0)
        self.running = False
        self.facing_direction = "south"

        self.animation_driver = None
        self.animation_state_machine: AnimationStateMachine | None = None
        self._external_animation_driver = False

        self.camera = None
        self.viewport_size = (1280, 720)
        self.mouse_to_world: Callable[[float, float], tuple[float, float]] | None = None
        self.attack_target_world = self.world_position
        self.attack_direction = (0.0, 1.0)

        self.audio = None
        self.sound_loader: Callable[[Any], Any] | None = None
        self.floor_type = "default"
        self.walk_sounds: dict[str, Any] = {}
        self.run_sounds: dict[str, Any] = {}
        self.roll_sound = None
        self.attack_sound = None
        self.get_hit_sound = None
        self.critical_hit_sound = None
        self.footstep_interval_walk = 0.42
        self.footstep_interval_run = 0.28
        self._footstep_timer = 0.0

        self.max_health = 100.0
        self.health = 100.0
        self.invulnerable = False
        self.injury_threshold = 0.5
        self.heavy_injury_threshold = 0.25

        self.weapon_profiles: dict[str, AttackProfile] = {}
        self.tool_profiles: dict[str, AttackProfile] = {}
        self.active_weapon: str | None = None
        self.active_tool: str | None = None
        self.default_attack = AttackProfile("unarmed")

        self._roll_requested = False
        self._attack_requested = False
        self._pending_damage_state: str | None = None
        self._current_attack: AttackProfile | None = None
        self._roll_cooldown_timer = 0.0
        self._pre_roll_invulnerable = False

        self.state_machine = StateMachine(owner=self)
        for state_name in self._STATES:
            self.state_machine.add_state(_ControllerState(self, state_name))

        self.state_changed = self.create_signal("character.state_changed")
        self.direction_changed = self.create_signal("character.direction_changed")
        self.attack_started = self.create_signal("character.attack_started")
        self.attack_performed = self.create_signal("character.attack_performed")
        self.damaged = self.create_signal("character.damaged")
        self.health_changed = self.create_signal("character.health_changed")
        self.footstep = self.create_signal("character.footstep")

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_input(self, input_manager, *, bind_defaults: bool = False) -> None:
        self.input = input_manager
        if bind_defaults:
            self.bind_default_actions(input_manager)

    def bind_default_actions(self, input_manager=None) -> None:
        manager = input_manager or self.input
        if manager is None:
            raise ValueError("An InputManager is required.")
        actions = manager.actions() if callable(getattr(manager, "actions", None)) else {}
        for action, key in self.DEFAULT_BINDINGS.items():
            if action not in actions:
                manager.bind_key(action, key)
        attack = self.input_actions["attack"]
        actions = manager.actions() if callable(getattr(manager, "actions", None)) else actions
        if attack not in actions:
            manager.bind_mouse(attack, "LEFT")

    def set_animation_driver(self, driver) -> None:
        if driver is not None and not callable(getattr(driver, "play", None)):
            raise TypeError("Animation driver must provide play(name, restart=False).")
        self.animation_driver = driver
        self._external_animation_driver = bool(
            driver is not None and getattr(driver, "parent", None) is not self
        )
        self.animation_state_machine = None
        self._rebuild_animation_states()

    def set_camera(self, camera, *, viewport_size: tuple[int, int] | None = None) -> None:
        self.camera = camera
        if viewport_size is not None:
            self.viewport_size = (int(viewport_size[0]), int(viewport_size[1]))

    def set_mouse_to_world(self, callback: Callable[[float, float], tuple[float, float]] | None) -> None:
        self.mouse_to_world = callback

    def set_audio(self, audio_system, *, sound_loader: Callable[[Any], Any] | None = None) -> None:
        self.audio = audio_system
        self.sound_loader = sound_loader

    def set_floor_type(self, floor_type: str) -> None:
        self.floor_type = str(floor_type)

    def set_footstep_sound(self, movement: str, floor_type: str, sound: Any) -> None:
        target = self.walk_sounds if str(movement).lower() == "walk" else self.run_sounds
        target[str(floor_type)] = sound

    def set_weapon(self, name: str | None, profile: AttackProfile | Mapping[str, Any] | None = None) -> None:
        self.active_weapon = None if name is None else str(name)
        if name is not None and profile is not None:
            self.weapon_profiles[str(name)] = self._coerce_profile(str(name), profile)

    def set_tool(self, name: str | None, profile: AttackProfile | Mapping[str, Any] | None = None) -> None:
        self.active_tool = None if name is None else str(name)
        if name is not None and profile is not None:
            self.tool_profiles[str(name)] = self._coerce_profile(str(name), profile)

    def register_weapon(self, name: str, profile: AttackProfile | Mapping[str, Any]) -> AttackProfile:
        result = self._coerce_profile(name, profile)
        self.weapon_profiles[str(name)] = result
        return result

    def register_tool(self, name: str, profile: AttackProfile | Mapping[str, Any]) -> AttackProfile:
        result = self._coerce_profile(name, profile)
        self.tool_profiles[str(name)] = result
        return result

    @staticmethod
    def _coerce_profile(name: str, profile: AttackProfile | Mapping[str, Any]) -> AttackProfile:
        if isinstance(profile, AttackProfile):
            return profile
        return AttackProfile(
            name=str(name),
            animation=profile.get("animation"),
            duration=max(0.01, float(profile.get("duration", 0.35))),
            sound=profile.get("sound"),
            damage=max(0.0, float(profile.get("damage", 0.0))),
        )

    # ------------------------------------------------------------------
    # Runtime input and state machine
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> str | None:
        return self.state_machine.current_name

    def _action(self, action: str, kind: str) -> bool:
        manager = self.input
        if manager is None:
            return False
        value = getattr(manager, f"action_{kind}", None)
        if callable(value):
            try:
                return bool(value(action))
            except (KeyError, TypeError):
                return False
        if isinstance(value, Mapping):
            return bool(value.get(action, False))
        method = getattr(manager, f"is_action_{kind}", None)
        return bool(method(action)) if callable(method) else False

    def _read_input(self) -> None:
        actions = self.input_actions
        x = float(self._action(actions["right"], "down")) - float(self._action(actions["left"], "down"))
        y = float(self._action(actions["down"], "down")) - float(self._action(actions["up"], "down"))
        length = math.hypot(x, y)
        if length > 1.0:
            x /= length
            y /= length
        self.input_vector = (x, y)
        self.running = bool(length > 0.0 and self._action(actions["run"], "down"))
        if length > 0.0:
            self._set_facing(self._direction_from_vector(x, y))
        if self._action(actions["roll"], "pressed"):
            self._roll_requested = True
        if self._action(actions["attack"], "pressed"):
            self._attack_requested = True

    def update(self, delta_time: float) -> None:
        delta = max(0.0, float(delta_time))
        self._roll_cooldown_timer = max(0.0, self._roll_cooldown_timer - delta)
        self._read_input()

        if not self.state_machine.running:
            self.state_machine.start("idle")

        desired = self._desired_state()
        if desired != self.current_state:
            self.state_machine.change_state(desired)
        self.state_machine.update(delta)

        if self._external_animation_driver and self.animation_driver is not None:
            self.animation_driver.update(delta)
        if self.animation_state_machine is not None:
            self.animation_state_machine.update()

    def _desired_state(self) -> str:
        current = self.current_state
        if current == "dead":
            return "dead"
        if current in self._TRANSIENT_STATES:
            duration = self._state_duration(current)
            if self.state_machine.state_time < duration:
                return current
        if self._pending_damage_state is not None:
            result = self._pending_damage_state
            self._pending_damage_state = None
            return result
        if self._roll_requested and self._roll_cooldown_timer <= 0.0 and self.input_vector != (0.0, 0.0):
            self._roll_requested = False
            return "roll"
        if self._attack_requested:
            self._attack_requested = False
            return "attack"
        if self.input_vector == (0.0, 0.0):
            return "idle"
        return "run" if self.running else "walk"

    def _state_duration(self, state: str) -> float:
        if state == "roll":
            return self.roll_duration
        if state == "attack" and self._current_attack is not None:
            return self._current_attack.duration
        return {"get_hit": 0.28, "get_critical_hit": 0.42, "injured": 0.35, "heavily_injured": 0.5}.get(state, 0.0)

    def _on_state_enter(self, state: str, payload: Any = None) -> None:
        if state == "roll":
            self._pre_roll_invulnerable = self.invulnerable
            self.invulnerable = True
            self._roll_cooldown_timer = self.roll_cooldown + self.roll_duration
            direction = self._vector_from_direction(self.facing_direction)
            self.velocity.set(direction[0] * self.roll_speed, direction[1] * self.roll_speed)
            self._play_sound(self.roll_sound)
        elif state == "attack":
            self._current_attack = self._selected_attack()
            self.attack_target_world, self.attack_direction = self._get_attack_target()
            self.attack_started.emit(self, self._current_attack, self.attack_target_world, self.attack_direction)
            self._play_sound(self._current_attack.sound or self.attack_sound)
        elif state == "dead":
            self.velocity.clear()
        elif state in {"get_hit", "get_critical_hit", "injured", "heavily_injured"}:
            self._play_sound(self.critical_hit_sound if state == "get_critical_hit" else self.get_hit_sound)
        self._play_animation(
            state,
            custom_animation=(
                self._current_attack.animation
                if state == "attack" and self._current_attack is not None
                else None
            ),
        )
        self.state_changed.emit(self, state)

    def _on_state_exit(self, state: str, next_state: str | None) -> None:
        if state == "attack" and self._current_attack is not None:
            self.attack_performed.emit(self, self._current_attack, self.attack_target_world, self.attack_direction)
            self._current_attack = None
        if state == "roll":
            self.invulnerable = self._pre_roll_invulnerable
            self.velocity.clear()

    def _update_controller_state(self, state: str, delta: float) -> None:
        if state in {"idle", "walk", "run"}:
            self._update_locomotion(delta)
        elif state == "roll":
            self.move_and_slide(delta)
        elif state == "attack":
            self._move_towards_velocity(0.0, 0.0, self.friction, delta)
            self.move_and_slide(delta)
        else:
            self._move_towards_velocity(0.0, 0.0, self.friction, delta)
            self.move_and_slide(delta)

        if state in {"walk", "run"}:
            self._update_footsteps(state, delta)

    def _update_locomotion(self, delta: float) -> None:
        x, y = self.input_vector
        speed = self.run_speed if self.running else self.walk_speed
        self._move_towards_velocity(x * speed, y * speed, self.acceleration if (x or y) else self.friction, delta)
        self.move_and_slide(delta)

    def _move_towards_velocity(self, target_x: float, target_y: float, rate: float, delta: float) -> None:
        step = max(0.0, float(rate)) * delta
        self.velocity.x = self._move_towards(self.velocity.x, target_x, step)
        self.velocity.y = self._move_towards(self.velocity.y, target_y, step)

    @staticmethod
    def _move_towards(value: float, target: float, step: float) -> float:
        if abs(target - value) <= step:
            return target
        return value + math.copysign(step, target - value)

    # ------------------------------------------------------------------
    # Directions and animations
    # ------------------------------------------------------------------

    def _set_facing(self, direction: str) -> None:
        if direction == self.facing_direction:
            return
        previous = self.facing_direction
        self.facing_direction = direction
        self.direction_changed.emit(self, previous, direction)
        if self.current_state is not None:
            self._play_animation(self.current_state)

    @classmethod
    def _direction_from_vector(cls, x: float, y: float) -> str:
        if x == 0.0 and y == 0.0:
            return "south"
        index = int(round((math.atan2(y, x) / (math.pi / 4.0)))) % 8
        return ("east", "south_east", "south", "south_west", "west", "north_west", "north", "north_east")[index]

    @classmethod
    def _vector_from_direction(cls, direction: str) -> tuple[float, float]:
        angle = {
            "east": 0.0, "south_east": math.pi / 4.0, "south": math.pi / 2.0,
            "south_west": 3.0 * math.pi / 4.0, "west": math.pi,
            "north_west": -3.0 * math.pi / 4.0, "north": -math.pi / 2.0,
            "north_east": -math.pi / 4.0,
        }.get(direction, math.pi / 2.0)
        return math.cos(angle), math.sin(angle)

    def _rebuild_animation_states(self) -> None:
        driver = self.animation_driver
        if driver is None:
            self.animation_state_machine = None
            return
        machine = AnimationStateMachine(driver)
        for state in self._STATES:
            animation = self._find_animation(state)
            if animation is not None:
                machine.add_state(state, animation)
        self.animation_state_machine = machine

    def _find_animation(self, state: str, custom_animation: str | None = None) -> str | None:
        driver = self.animation_driver
        if driver is None:
            return None
        direction = self.facing_direction
        abbreviation = self._DIRECTION_ABBREVIATIONS[direction]
        candidates: list[str] = []
        if custom_animation:
            try:
                candidates.extend(
                    [
                        str(custom_animation).format(
                            direction=direction,
                            dir=abbreviation,
                            weapon=self.active_weapon or "unarmed",
                            tool=self.active_tool or "none",
                        ),
                        str(custom_animation),
                    ]
                )
            except (KeyError, IndexError, ValueError):
                candidates.append(str(custom_animation))
        candidates.extend([f"{state}_{direction}", f"{state}_{abbreviation}"])
        for name in candidates:
            if callable(getattr(driver, "has_animation", None)) and driver.has_animation(name):
                return name
        return None

    def _play_animation(self, state: str, *, custom_animation: str | None = None) -> None:
        driver = self.animation_driver
        if driver is None:
            return
        animation = self._find_animation(state, custom_animation)
        if animation is None:
            return
        if (
            self.animation_state_machine is None
            or self.animation_state_machine.player is not driver
            or state not in self.animation_state_machine.states
            or self.animation_state_machine.animation_for(state) != animation
        ):
            self._rebuild_animation_states()
            if custom_animation:
                self.animation_state_machine.add_state(state, animation)
        machine = self.animation_state_machine
        if machine is not None and state in machine.states:
            machine.set_state(state)

    # ------------------------------------------------------------------
    # Combat and target selection
    # ------------------------------------------------------------------

    def _selected_attack(self) -> AttackProfile:
        if self.active_weapon is not None and self.active_weapon in self.weapon_profiles:
            return self.weapon_profiles[self.active_weapon]
        if self.active_tool is not None and self.active_tool in self.tool_profiles:
            return self.tool_profiles[self.active_tool]
        return self.default_attack

    def _get_attack_target(self) -> tuple[tuple[float, float], tuple[float, float]]:
        position = getattr(self.input, "mouse_position", (0.0, 0.0))
        try:
            mouse_x, mouse_y = float(position[0]), float(position[1])
        except (TypeError, ValueError, IndexError):
            mouse_x, mouse_y = self.world_position
        if self.mouse_to_world is not None:
            target = self.mouse_to_world(mouse_x, mouse_y)
        elif self.camera is not None and callable(getattr(self.camera, "screen_to_world", None)):
            target = self.camera.screen_to_world(mouse_x, mouse_y, *self.viewport_size)
        else:
            target = (mouse_x, mouse_y)
        dx, dy = float(target[0]) - self.world_position[0], float(target[1]) - self.world_position[1]
        length = math.hypot(dx, dy)
        if length <= 0.00001:
            direction = self._vector_from_direction(self.facing_direction)
        else:
            direction = (dx / length, dy / length)
            self._set_facing(self._direction_from_vector(*direction))
        return (float(target[0]), float(target[1])), direction

    def take_damage(self, amount: float, *, critical: bool = False, source: Any = None) -> bool:
        amount = max(0.0, float(amount))
        if amount <= 0.0 or self.invulnerable or self.health <= 0.0:
            return False
        previous = self.health
        self.health = max(0.0, min(self.max_health, self.health - amount))
        if self.health <= 0.0:
            state = "dead"
        elif critical:
            state = "get_critical_hit"
        elif self.health / self.max_health <= self.heavy_injury_threshold:
            state = "heavily_injured"
        elif self.health / self.max_health <= self.injury_threshold:
            state = "injured"
        else:
            state = "get_hit"
        self._pending_damage_state = state
        self.damaged.emit(self, amount, previous, self.health, critical, source)
        self.health_changed.emit(self, previous, self.health)
        return True

    def heal(self, amount: float) -> float:
        previous = self.health
        self.health = min(self.max_health, self.health + max(0.0, float(amount)))
        if self.health != previous:
            self.health_changed.emit(self, previous, self.health)
        return self.health - previous

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def _update_footsteps(self, movement: str, delta: float) -> None:
        if self.input_vector == (0.0, 0.0):
            self._footstep_timer = 0.0
            return
        interval = self.footstep_interval_run if movement == "run" else self.footstep_interval_walk
        self._footstep_timer += delta
        if self._footstep_timer < interval:
            return
        self._footstep_timer -= interval
        sounds = self.run_sounds if movement == "run" else self.walk_sounds
        sound = sounds.get(self.floor_type, sounds.get("default"))
        self._play_sound(sound)
        self.footstep.emit(self, movement, self.floor_type, sound)

    def _play_sound(self, sound: Any) -> None:
        if sound is None or self.audio is None:
            return
        if isinstance(sound, (str, bytes)) and self.sound_loader is not None:
            sound = self.sound_loader(sound)
        elif isinstance(sound, (str, bytes)) and callable(getattr(self.audio, "load", None)):
            sound = self.audio.load(sound)
        if sound is None:
            return
        from nexora.audio import AudioChannel, AudioSource
        source = AudioSource(sound, channel=AudioChannel.SFX, position=self.world_position)
        player = getattr(self.audio, "player", None)
        if player is not None and callable(getattr(player, "play", None)):
            player.play(source)


__all__ = ["AttackProfile", "CharacterController2D"]
