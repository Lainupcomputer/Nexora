# CharacterController2D

`CharacterController2D` is a `CharacterBody2D` node with input, movement,
animation, combat and spatial sound hooks.

```python
from nexora.nodes import AnimatedSprite, CharacterController2D

player = CharacterController2D("Player", scene.world)
sprite = AnimatedSprite("Sprite", scene.world)
player.add_child(sprite)
player.set_animation_driver(sprite)
player.set_input(input_manager, bind_defaults=True)
player.set_camera(camera, viewport_size=(1280, 720))
player.set_audio(audio_system, sound_loader=assets.sound)
scene.root.add_child(player)
```

The default bindings are WASD, left Shift, Space and left mouse button. For
custom controls, replace entries in `player.input_actions` and bind those
actions through `InputManager`.

Animation names use eight direction suffixes, for example:

```text
idle_south       walk_south       run_south
roll_south       get_hit_south   get_critical_hit_south
injured_south    heavily_injured_south
```

Register weapon/tool attacks with an optional `{direction}`, `{dir}`,
`{weapon}` or `{tool}` placeholder:

```python
player.register_weapon(
    "sword",
    {
        "animation": "attack_{weapon}_{direction}",
        "duration": 0.30,
        "damage": 25,
        "sound": assets.sound("audio/sword.wav"),
    },
)
player.set_weapon("sword")
```

Call `set_floor_type("grass")` when the character enters a different floor
type and configure sounds with `set_footstep_sound("walk", "grass", sound)`
and `set_footstep_sound("run", "grass", sound)`.

Attacks expose `attack_target_world` and `attack_direction` and emit
`attack_started`/`attack_performed`, so gameplay code can apply hit detection
or spawn projectiles at the mouse-directed target.
