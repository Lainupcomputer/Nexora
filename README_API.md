# Nexora Engine — Public API Reference

This document is the practical reference for the public Python API of the Nexora Engine.
It describes the API exported by the `main` branch (package version `0.1.0`) and is intended
for game projects, examples, and engine contributors.

> Nexora is in early development. Public names are usable today, but signatures,
> serialization formats, and subsystem behavior can still change.

- Project overview: [README.md](README.md)
- Examples: [examples/](examples/)
- Source package: [nexora/](nexora/)

## 1. Requirements and installation

Nexora currently targets:

- Python 3.13 or newer
- SDL3 libraries available through PySDL3
- an SDL_GPU-compatible graphics environment for rendering
- an SDL3 audio device for runtime audio initialization

Install the package from a checkout:

~~~bash
python -m pip install -e .
~~~

Install the development dependencies (including pytest):

~~~bash
python -m pip install -e ".[dev]"
~~~

Nexora is designed to work well with Python's free-threaded build. To run the
same mode used by CI, use a free-threaded interpreter and `-Xgil=0`.

The package sets `SDL_GPU_DRIVER` to `vulkan` when the variable is not already set.
Set the environment variable before importing `nexora` when another SDL_GPU backend
is required.

## 2. Import conventions

The high-level entry point is intentionally small:

~~~python
from nexora import Game, Engine
~~~

Subsystems are re-exported from their package namespace:

~~~python
from nexora.assets import AssetManager
from nexora.audio import AudioSystem
from nexora.input import InputManager
from nexora.nodes import Node, Camera2D
from nexora.rendering import Renderer
from nexora.scene import Scene, SceneManager
from nexora.tilemap import TileMap, TileSet
~~~

Prefer these package-level imports over importing private implementation modules.
The export inventory is listed in [Public exports](#public-exports).

## 3. Minimal game

A game normally subclasses `Game` and overrides only the callbacks it needs:

~~~python
from nexora import Game
from nexora.scene import Scene

class MyGame(Game):
    def initialize(self) -> None:
        main_scene = Scene("Main")
        self.scene = main_scene

    def update(self, delta_time: float) -> None:
        if self.input.is_action_pressed("quit"):
            self.stop()

MyGame(
    project_name="MyGame",
    title="My Game",
    width=1280,
    height=720,
    target_fps=144,
).run()
~~~

`Game.run()` creates the engine, binds runtime services, initializes the global
overlay, enters the loop, and shuts services down in a `finally` block.

## 4. Runtime lifecycle

The callback order for a normal frame is:

1. input state is advanced with `InputManager.begin_frame(events)`
2. raw SDL events are passed to `Game.handle_event(event)`
3. `Game.update(delta_time)` runs
4. zero or more `Game.fixed_update(fixed_delta_time)` steps run
5. audio is updated
6. `Game.render(interpolation)` runs
7. the renderer ends the frame and input is finalized

Override these `Game` methods:

| Callback | Purpose |
| --- | --- |
| `initialize()` | Create the initial scene, bindings, and game resources. |
| `handle_event(event)` | Handle raw SDL events that are not covered by input actions. |
| `update(delta_time)` | Variable-timestep gameplay and scene updates. |
| `fixed_update(fixed_delta_time)` | Deterministic physics or simulation work. |
| `render(interpolation)` | Custom drawing after scene updates. |
| `shutdown()` | Release game-owned resources before engine shutdown. |

`Game.stop()` requests loop termination. `Game.run()` must not be called again on a
game instance that has already completed shutdown.

### Game constructor

The constructor accepts project, window, timing, and save overrides. `None` means
“use the corresponding settings file”.

~~~python
Game(
    *,
    project_name="Nexora",
    title="Nexora",
    target_fps=None,
    fixed_delta_time=None,
    width=None,
    height=None,
    resizable=None,
    fullscreen=None,
    window_mode=None,       # WindowMode or "windowed"/"borderless"/"fullscreen"
    vsync=None,
    frames_in_flight=None,
    save_path=None,
    save_signing_key=...,
    scene_signing_key=None,
    save_version=1,
    save_max_file_size=64 * 1024 * 1024,
    quick_save_enabled=True,
    quick_save_slot="quicksave",
    autosave_enabled=True,
    autosave_slots=3,
    autosave_prefix="autosave",
)
~~~

### Game properties and services

| Member | Description |
| --- | --- |
| `project_name`, `title` | Project identity and window title. |
| `engine` | The `Engine` created by `run()`; `None` before startup. |
| `renderer`, `input`, `assets`, `audio` | Bound runtime services after initialization. |
| `scene`, `scenes` | Active scene and the `SceneManager` facade. |
| `scene_serializer` | Serializer used by the scene manager. |
| `saves` | The configured `SaveManager`. |
| `notifications` | Persistent notification center, when the overlay is initialized. |
| `logger` | Engine logger. |
| `time`, `delta_time`, `total_time`, `frame` | Current timing values. |
| `window_mode`, `vsync`, `fullscreen` | Current graphics state. |
| `running` | Whether the game loop is active. |
| `paths` | Resolved project and settings paths. |

Convenience methods include `set_windowed()`, `set_borderless()`,
`set_fullscreen()`, `set_window_mode(mode)`, `toggle_fullscreen()`,
`set_vsync(enabled)`, `reload_input_bindings()`, `save_input_bindings()`,
`reset_input_bindings()`, `reload_engine_settings()`,
`reset_engine_settings()`, `apply_graphics_settings()`,
`reset_graphics_settings()`, `apply_audio_settings()`, and
`reset_audio_settings()`.

### Engine

`Engine` is the service container used by `Game`. It exposes:

- time: `time`, `delta_time`, `unscaled_delta_time`, `total_time`,
  `fixed_time`, `frame`, and `fixed_frame`
- lifecycle: `initialize()`, `run()`, `stop()`, and `shutdown()`
- settings operations: `reload_engine_settings()`, `reset_engine_settings()`,
  `apply_graphics_settings()`, `reset_graphics_settings()`,
  `apply_audio_settings()`, `reset_audio_settings()`
- input persistence: `reload_input_bindings()`, `save_input_bindings()`,
  `reset_input_bindings()`

Most game code should use the services exposed by `Game`; use `Engine` directly
when building tooling or a custom host.

## 5. Scenes and node trees

### Scene

~~~python
from nexora.scene import Scene

scene = Scene("Main")
player = scene.create_node("Player")
scene.add_node(player)
self.scene = scene
~~~

Important `Scene` members:

| API | Description |
| --- | --- |
| `state`, `active`, `paused`, `destroyed` | Lifecycle state. |
| `camera` / `set_camera(node)` / `clear_camera()` | Scene camera selection. |
| `enter()`, `exit()`, `pause()`, `resume()` | Lifecycle transitions. |
| `on_enter(previous_state)` | Override hook after activation. |
| `on_exit(previous_state)` | Override hook before leaving. |
| `on_pause()`, `on_resume()` | Override pause hooks. |
| `create_node(name, parent=None, node_type=Node)` | Construct and attach a node. |
| `add_node(node, parent=None)`, `remove_node(node)` | Manage the tree. |
| `find(name)` | Find a node by name. |
| `update(dt)`, `fixed_update(dt)`, `render(interpolation)` | Scene callbacks. |
| `update_input(input_manager)` | Forward input to UI and scene nodes. |
| `destroy()` | Destroy the scene and its nodes. |

`SceneState` contains the scene lifecycle values used by the manager.

### SceneManager

`Game.scenes` is the single source of truth for loaded and active scenes.

~~~python
from nexora.scene import Scene

self.scenes.register("Main", lambda: Scene("Main"))
self.scenes.register("Pause", lambda: Scene("Pause"), keep_loaded=True)
self.scenes.change_scene("Main")
~~~

Common operations:

- registration: `register()`, `unregister()`, `is_registered()`, `registration()`
- loading: `load()`, `load_registered()`, `ensure_loaded()`, `reload()`, `unload()`
- activation: `activate()`, `change_scene()`, `deactivate()`
- stack flow: `push_scene()`, `pop_scene()`, `pop_scene_and_unload()`,
  `clear_stack()`
- state queries: `active_scene`, `active_scene_name`, `scenes`, `scene_names`,
  `stack`, `stack_names`, `stack_depth`, `is_loaded()`, `is_active()`,
  `is_on_stack()`
- transitions/loading: `SceneTransition`, `FadeSceneTransition`,
  `begin_loading()`, `begin_serialized_loading()`, `LoadingScene`,
  `SceneLoadTask`
- serialized scenes: `register_serialized()`, `load_serialized_registered()`,
  `serialized_registration()`, `serialized_names()`, and
  `resolve_serialized_scene_name()`

### Node

`Node` is the base class for gameplay, world, and UI tree objects.

~~~python
from nexora.nodes import Node

class Player(Node):
    def update(self, delta_time: float) -> None:
        pass

player = Player("Player")
scene.add_node(player)
~~~

Node API groups:

- transforms: `world_position`, `world_rotation`, `world_scale`, `world_transform`
- callbacks: `update()`, `fixed_update()`, `render()`,
  `update_tree()`, `fixed_update_tree()`, `render_tree()`
- hierarchy: `add_child()`, `remove_child()`, `find_child()`, `tree_root`,
  `iter_tree()`, `iter_ancestors()`, `is_descendant_of()`
- signals: `create_signal(name)`
- lifetime: `destroy()`

Built-in node families are re-exported from `nexora.nodes`: cameras, physics
bodies, particle and light nodes, navigation nodes, `AnimatedSprite`, `TileMapNode`,
and the UI controls listed below.

## 6. Rendering

Use the high-level `Renderer` from `Game.renderer` in `render()` or a node's
`render()` callback.

~~~python
def render(self, interpolation: float) -> None:
    renderer = self.renderer
    renderer.sprite(
        self.player_texture,
        320,
        180,
        width=64,
        height=64,
        alpha=1.0,
    )
    renderer.rect(
        640,
        360,
        160,
        80,
        color=(0.8, 0.2, 0.3, 1.0),
        radius=8,
    )
~~~

### Renderer surface

Properties: `width`, `height`, `size`, `driver`, `camera`,
`post_processing`, and `post_processor`.

Frame methods:

- `begin_frame()` -> `bool`
- `end_frame()` -> `bool`
- `resize(width, height)`
- `destroy()`

Drawing methods:

- sprites: `sprite(...)`, `sprites(...)`
- shapes: `rect(...)`, `pixel(...)`, `line(...)`, `circle(...)`,
  `ellipse(...)`, `triangle(...)`, `polygon(...)`
- text: `text(...)`, `text_measure(text, scale=1)`,
  `text_baseline(scale=1)`
- snapshots: `submit(snapshot, texture, layer=0)`

Most draw calls accept a `layer` argument. `sprite()` additionally supports
rotation, origin, alpha, flips, and a normalized UV rectangle.

World/screen helpers:

- `world_scope()` and `overlay_scope()` are context managers for render phases.
- `render_phase` and `set_render_phase(phase)` select the active phase.
- `clip_rect`, `push_clip_rect(...)`, `pop_clip_rect()`,
  `clear_clip_rects()` manage nested clipping.

### Cameras and GPU layer

`nexora.rendering.Camera` is the high-level camera type. Node-based camera
controllers include `Camera2D`, `FollowCamera2D`, `FreeCamera2D`,
`CinematicCamera2D`, and `FixedCamera2D`.

The advanced GPU namespace exports `GPUContext`, `GPUShader`, `GPUPipeline`,
`GPUBuffer`, `GPUTexture`, `GPUSampler`, `GPURenderer`, `GPUSpriteBatch`,
`RenderSnapshot`, and `WindowMode`. Use this layer for custom pipelines or
renderer extensions; normal gameplay should use `Renderer`.

Post-processing types are available from `nexora.rendering.postprocessing`:
`PostProcess` and `PostProcessEffects`.

## 7. Input

Input is action based and is updated by the engine once per frame.

~~~python
def initialize(self) -> None:
    self.input.bind_key("jump", "SPACE")
    self.input.bind_mouse("fire", 1)

def update(self, delta_time: float) -> None:
    if self.input.is_action_pressed("jump"):
        self.player.jump()
    if self.input.is_action_down("fire"):
        self.player.fire()
~~~

`InputManager` API:

- setup and bindings: `initialize(window=None)`, `bind()`, `bind_key()`,
  `bind_mouse()`, `unbind()`, `clear_bindings()`
- persistence: `load_bindings()`, `reload_bindings()`, `save_bindings()`,
  `reset_bindings()`, `settings_path`, `keybinds_path`
- frame processing: `begin_frame(events=())`, `end_frame()`
- keyboard: `key_down()`, `key_pressed()`, `key_released()`,
  `is_down()`, `is_pressed()`, `is_released()`
- mouse: `mouse_down()`, `mouse_pressed()`, `mouse_released()`,
  `mouse_position`, `mouse_delta`, `wheel`, `mouse_buttons_down`
- actions: `action_state()`, `action()`, `actions`,
  `is_action_down()`, `is_action_pressed()`, `is_action_released()`
- text input: `set_action_capture()`, `acquire_text_input()`,
  `release_text_input()`, `start_text_input()`, `stop_text_input()`,
  `text_input`, `text_input_active`, `text_input_started`,
  `text_input_stopped`
- window state: `focused`, `keys_down`, `keys_pressed`, `keys_released`

`Binding`, `BindingType`, `ActionState`, and `ActionStateProxy` are public data
types for custom binding and UI integrations.

## 8. Assets

`AssetManager` is available as `game.assets`. Paths are resolved through the
configured asset root and cached by type.

~~~python
texture = self.assets.load_texture("sprites/player.png")
font = self.assets.load_font("fonts/ui.ttf", 18)
sound = self.assets.sound("audio/click.wav")

self.assets.preload(
    textures=("sprites/player.png",),
    fonts=(("fonts/ui.ttf", 18),),
    sounds=("audio/click.wav",),
)
~~~

Core methods:

- generic: `load()`, `get()`, `is_loaded()`, `is_loading()`,
  `is_failed()`, `unload()`, `clear()`
- paths/loaders: `resolve()`, `exists()`, `register_loader()`,
  `unregister_loader()`
- textures: `load_texture()`, `image()`, `texture()`, `get_texture()`,
  `is_texture_loaded()`, `unload_texture()`
- fonts: `load_font()`, `font()`, `get_font()`, `is_font_loaded()`,
  `unload_font()`
- audio: `sound()`, `get_sound()`, `is_sound_loaded()`,
  `unload_sound()`
- bulk loading: `preload()`, `add_loading_stages()`, `update()`
- groups: `register_group()`, `unregister_group()`, `get_group()`,
  `group_names()`, `loaded_groups()`, `load_group()`, `load_groups()`,
  `unload_group()`, `unload_groups()`, `clear_groups()`

Use `bind_gpu()` and `bind_audio_cache()` when hosting an `AssetManager`
outside the normal `Engine` setup.

## 9. Audio

The audio facade is `game.audio`. Audio initialization requires an available
SDL3 audio device; a machine or CI runner without one must skip audio-dependent
tests and runtime checks.

~~~python
music = self.audio.load("music/theme.wav")
self.audio.music.play(music)
self.audio.set_bus_volume("Music", 0.75)
self.audio.set_bus_muted("SFX", False)
~~~

`AudioSystem` exposes:

- device state: `initialized`, `frequency`, `channels`,
  `target_queue_frames`, `max_update_frames`
- lifecycle: `initialize()`, `shutdown()`, `reset()`
- channels: `set_volume()`, `get_volume()`, `get_effective_volume()`
- sounds/cache: `load()`, `unload()`, `clear_cache()`
- buses: `get_bus()`, `set_bus_volume()`, `get_bus_volume()`,
  `set_bus_muted()`, `get_bus_muted()`
- players: `player` (`AudioPlayer`), `music` (`MusicPlayer`),
  `mixer`, `device`, and `cache`

`AudioSource` supports volume, bus, pitch, looping, 2D position and distance
parameters, seeking, fade-in/fade-out, `play()`, `pause()`, `resume()`,
and `stop()`. `AudioPlayer` manages multiple sources and mixing.
`MusicPlayer` supports queueing, shuffle, repeat modes, previous/next,
pause/resume, and stop.

## 10. ECS

The ECS API is available from `nexora.ecs`.

~~~python
from nexora.ecs import Transform, World

world = World()
entity = world.create_entity()
world.add_component(entity, Transform())

for entity, transform in world.query(Transform):
    transform.position = (0.0, 0.0)
~~~

`World` provides `create_entity()`, `destroy_entity()`, `is_alive()`,
`entity_count()`, component add/remove/get/has operations, `query()`,
`add_system()`, `remove_system()`, `update()`, `fixed_update()`,
`render()`, and `shutdown()`.

Built-in components are `Transform`, `Velocity`, `Sprite`, and `Health`.
Subclass `System` and override `initialize(world)`, `update(world, dt)`,
`fixed_update(world, fixed_dt)`, `render(world, interpolation)`, and
`shutdown(world)`.

`ECSSystemScheduler` adds read/write declarations, priorities,
`main_thread_only`, explicit dependencies, conflict detection, parallel
batches, deterministic ordering, and cycle errors
(`ECSDependencyError`, `ECSDependencyCycleError`).

`ArchetypeWorld`, `Archetype`, and `Chunk` are the lower-level storage API.
Use them when profiling shows that the regular `World` abstraction is not enough.

## 11. Physics and collision

Gameplay-facing physics nodes are re-exported from `nexora.nodes`:

- `Body2D` — base body with collision layers/masks and AABB queries
- `StaticBody2D` — non-moving collider
- `CharacterBody2D` — `move_and_slide()` and `move_and_collide()`
- `Area2D` — overlap detection and entered/exited callbacks
- `CollisionShape2D` — rectangular shape and point/shape overlap tests
- `RayCast2D` — configurable ray queries
- `Vector2` and `BodyMoveResult` — movement helpers/results

`PhysicsWorld2D` and `get_physics_world()` are available from
`nexora.physics`. The world supports body registration, broad-phase rebuilds,
AABB queries, and synchronization. `KinematicCollision2D` and `RayCastHit2D`
represent collision results.

Typical flow:

1. create a body node and one or more collision shapes
2. configure its collision layer and mask
3. use `move_and_slide()` or `move_and_collide()` in `fixed_update()`
4. inspect slide collisions or raycast results
5. use `Area2D` overlap signals for triggers

## 12. Animation

Animation clips can be generated from a sprite sheet:

~~~python
from nexora.animation import AnimationClip, AnimationSet, Animator

walk = AnimationClip.from_row(
    "walk",
    row=0,
    frame_count=6,
    columns=6,
    rows=4,
    fps=10,
)
animations = AnimationSet()
animations.add(walk)

animator = Animator()
animator.add_clip(walk)
animator.play("walk")
~~~

Public animation types:

- `AnimationFrame`, `AnimationEvent`, `AnimationClip`
- `AnimationSet` with `add()`, `add_row()`, `add_grid()`, `get()`,
  `require()`, `has()`, `remove()`, `clear()`
- `Animator` with `play()`, `pause()`, `resume()`, `stop()`, `reset()`,
  `update()`, `current_clip`, `current_frame`, `frame_index`, `progress`,
  `speed_scale`, `playing`, and `finished`
- `AnimationPlayer` for binding clips to `AnimatedSprite`
- `AnimationStateMachine` and `AnimationTransition` for state-driven playback

`AnimationClip.with_event(frame, name, data)` attaches a callback/event payload
to a frame. Use `loop=False` for one-shot clips.

## 13. Tilemaps and isometric coordinates

The tilemap API is available from `nexora.tilemap`:

- `TileSet` — tile dimensions, UVs, regions, metadata, tags, solid flags,
  animations, and texture loading
- `TileMap` — map dimensions, layers, layer ordering, and coordinate conversion
- `TileLayer` — chunk-backed tile storage and bulk editing
- `TileChunk`, `TileChunkRenderCache`, `CachedTile` — chunk and render-cache types
- `TileMetadata`, `TileCollision`, `TileMoveResult` — gameplay metadata/collision
- `TileNavigation`, `NavigationPath`, `NavigationState` — pathfinding and blockers
- `TileProjection`, `EMPTY_TILE`, `TileAnimation`, `TileAnimationFrame`

Coordinate conversion:

~~~python
tile_x, tile_y = tile_map.world_to_tile(world_x, world_y)
world_x, world_y = tile_map.tile_to_world(tile_x, tile_y)
~~~

`TileMap` supports `create_layer()`, `add_layer()`, `get_layer()`,
`require_layer()`, `remove_layer()`, `move_layer()`, `contains()`,
`pixel_size`, and state conversion through `to_state()` / `from_state()`.

`TileLayer` supports `get_tile()`, `set_tile()`, `clear_tile()`, `fill()`,
`fill_rect()`, `clear_rect()`, `iter_tiles()`, `count_tiles()`,
`find_tiles()`, chunk iteration, dirty tracking, opacity, and state conversion.

`TileSet` provides `index(column, row)`, `cell(index)`, `uv(index)`,
`region(index)`, `pixel_rect(index)`, metadata/tag/solid queries,
animation resolution, `load_texture()`, and state conversion.

`TileNavigation.find_path(start, goal)` returns a `NavigationPath` (or `None`)
and supports dynamic blockers, traversal costs, optional blocked start/goal,
and world-space queries through `find_world_path()`.

## 14. UI

UI nodes are exported from `nexora.nodes`, not from the small `nexora.ui`
module. The scene root exposes a UI tree that is updated and rendered together
with the scene.

Base types:

- `UINode`, `UIRoot`
- `BoxContainer`, `VBoxContainer`, `HBoxContainer`
- `Panel`, `ScrollView`, `ListView`

Controls and feedback:

- `Button`, `CheckBox`, `Dropdown`
- `RadioButton`, `RadioButtonGroup`
- `Slider`, `TextInput`
- `Label`, `ProgressBar`
- `Tooltip`
- `NotificationCenter`, `NotificationAnchor`, `NotificationType`

UI nodes use the same node-tree lifetime model and add anchors, pivots,
measure/arrange layout, focus, hover, clipping, and pointer/text-input behavior.
`nexora.ui.UIInput` contains UI input integration helpers.

## 15. Particles and lighting

Particle types are exported by `nexora.particles`:

`Particle`, `ParticleConfig`, `ParticleSystem`, `ParticlePresets`,
`ParticleModule`, `SpawnShapeModule`, `LifetimeModule`, `VelocityModule`,
`GravityModule`, `SizeOverLifetimeModule`, `ColorOverLifetimeModule`,
`RotationModule`, and `BurstModule`.

`ParticleConfig.add_module()`, `get_module()`, `remove_modules()`,
`to_state()`, and `from_state()` are the main configuration operations.
`ParticleSystem` registers/unregisters emitters, reports emitter/particle counts,
and supports `clear()` and `stop_all(clear=False)`.

Lighting types are exported by `nexora.lighting`:

- `LightSnapshot`, `OccluderSnapshot`
- `LightingSystem`, `ScreenLight`, `ScreenShadowSegment`

`LightingSystem` can enable/disable lighting and shadows, set ambient color,
start a frame, submit lights/occluders, build screen-frame data, and apply
lighting through a post-process. Node-facing `Light2D` and `LightOccluder2D`
are available from `nexora.nodes`.

## 16. Save games

`Game.saves` is a signed, versioned save manager.

~~~python
metadata = self.saves.save(
    "slot-1",
    {"level": 3, "score": 1200},
    name="Checkpoint",
    playtime=self.total_time,
)

save_game = self.saves.load("slot-1")
print(save_game.data)

self.saves.quick_save({"level": 3})
if self.saves.has_quick_save():
    quick = self.saves.quick_load()
~~~

Main operations:

- configuration: `save_path`, `set_save_path()`, `set_signing_key()`,
  `quick_save_enabled`, `quick_save_slot`, `autosave_enabled`, `autosave_slots`,
  `autosave_prefix`
- manual slots: `save()`, `load()`, `exists()`, `delete()`, `list_slots()`,
  `metadata()`
- quick save: `quick_save()`, `quick_load()`, `has_quick_save()`,
  `delete_quick_save()`
- autosave: `auto_save()`, `list_auto_saves()`, `latest_auto_save_slot()`,
  `load_latest_auto_save()`, `has_auto_save()`, `delete_auto_saves()`
- events: `add_listener()`, `remove_listener()`, `clear_listeners()`

Use a game-specific `save_signing_key` in production. Handle
`SaveNotFoundError`, `SaveIntegrityError`, `InvalidSaveError`,
`UnsupportedSaveVersionError`, and `UnsafeSaveDataError` at load boundaries.

## 17. Signals and event bus

Signals are lightweight callback channels:

~~~python
from nexora.signals import EventBus, Signal

health_changed = Signal()
health_changed.connect(lambda value: print(value), once=True)
health_changed.emit(100)

events = EventBus()
events.connect("player_died", lambda: print("game over"))
events.emit("player_died")
~~~

`Signal.connect()` accepts `owner`, `once`, and `priority`.
`SignalConnection` provides `disconnect()`, `block()`, `unblock()`,
and `connected`. `Signal.disconnect()`, `is_connected()`, `emit()`,
and `clear()` manage listeners.

`EventBus` provides `signal(name)`, `connect()`, `emit()`, `clear()`,
and `has_signal()`.

## 18. Threading and task scheduling

Nexora supplies a worker scheduler and futures for non-rendering work.

~~~python
from nexora.threading import TaskPriority, TaskScheduler

scheduler = TaskScheduler(workers=2)
future = scheduler.submit(
    expensive_function,
    42,
    priority=TaskPriority.NORMAL,
)
result = future.result(timeout=2.0)
scheduler.shutdown()
~~~

`TaskScheduler` provides `start()`, `submit()`, `wait_all()`, `wait_any()`,
`cancel_all_pending()`, `stats()`, and worker/task counters.

`Future` provides `wait()`, `result()`, `exception()`, `cancel()`,
`done()`, `running()`, `pending()`, `status`, and `add_done_callback()`.

`ThreadContext` exposes `initialize()`, `initialize_worker()`,
`current_type()`, `is_main_thread()`, `is_worker_thread()`,
`assert_main_thread()`, and `assert_worker_thread()`.

Do not call SDL3 or GPU rendering APIs from worker threads. Use
`main_thread_only=True` in `ECSSystemScheduler.add_system()` when a system
must remain on the main thread.

## 19. Settings

Settings are layered: engine defaults are combined with user overrides.

The public settings services are:

- `EngineSettings` / `EngineSettingsStore`
- `GraphicsSettings` / `GraphicsSettingsStore`
- `AudioSettings` / `AudioSettingsStore`
- `LayeredSettingsStore` and `SettingsStore`

Each settings object supports `data`, `user_data`, `reload()`, `get(key, default)`,
`set(key, value)`, `save()`, `reset_user()`, and `remove_override(key)`.

Graphics settings additionally provide `gpu_context_kwargs()`,
`apply_post_processing(renderer)`, and `apply_runtime(context, renderer=None)`.

At game level, use `game.engine_settings`, `game.graphics_settings`,
`game.audio_settings`, then call the corresponding `apply_*`, `reload_*`,
or `reset_*` convenience method.

## 20. Scene serialization and prefabs

The serialization namespace is `nexora.scene.serialization` and is also
re-exported by `nexora.scene`.

Public building blocks:

- `SceneSerializer` and `PrefabSerializer`
- `NodeFactoryRegistry`
- `MigrationRegistry`
- `SceneLoadResult`
- `NodeAdapter`
- `SceneSerializationError`, `InvalidSceneFileError`,
  `SceneIntegrityError`, `SceneMigrationError`,
  `UnsupportedSceneVersionError`, `UnregisteredNodeTypeError`

Use `SceneManager.register_serialized(path, name=..., keep_loaded=...)` for
serialized scenes. Register custom node types with `NodeFactoryRegistry` and
version migrations with `MigrationRegistry`. Treat serialized files as
untrusted input and keep signing keys private.

## 21. Public exports

The following package-level names are the supported public surface. Individual
classes may expose additional properties documented in the sections above.

| Package | Main public types |
| --- | --- |
| `nexora` | `Game`, `Engine` |
| `nexora.animation` | `AnimationFrame`, `AnimationEvent`, `AnimationClip`, `Animator`, `AnimationSet`, `AnimationPlayer`, `AnimationStateMachine`, `AnimationTransition` |
| `nexora.assets` | `Asset`, `AssetStatus`, `AssetLoader`, `AssetManager`, `AssetCategory`, `AssetLoadCallbacks`, `AssetLoadProgress`, `AssetGroupDefinition`, `ImageData`, `TextureLoader`, `FontLoader`, `FontAssetRequest` |
| `nexora.audio` | `AudioSystem`, `AudioBuffer`, `AudioBus`, `AudioChannel`, `AudioDevice`, `AudioMixer`, `AudioPlayer`, `MusicPlayer`, `Sound`, `AudioSource`, `AudioSourceState`, `WavLoader`, `RepeatMode`, `AudioCache` |
| `nexora.debug` | `Logger`, `LogEvent`, `LogLevel`, `CommandContext`, `CommandRegistry`, `ConsoleCommand`, `ConsoleLevel`, `ConsoleLine`, `DebugConsole`, `ConsoleLogBridge`, `DebugMetrics`, `DebugSnapshot`, `GPUMetrics`, `DebugOverlay`, `PhysicsDebugRenderer` |
| `nexora.ecs` | `Entity`, `Transform`, `Velocity`, `Sprite`, `Health`, `System`, `World`, `ECSSystemScheduler`, `SystemAccess`, `ArchetypeWorld`, `Archetype`, `Chunk`, `ECSDependencyError`, `ECSDependencyCycleError` |
| `nexora.input` | `InputManager`, `Binding`, `BindingType`, `ActionState`, `ActionStateProxy`, `BindingStore` |
| `nexora.lighting` | `LightSnapshot`, `OccluderSnapshot`, `LightingSystem`, `ScreenLight`, `ScreenShadowSegment` |
| `nexora.nodes` | `Node`, camera nodes, physics nodes, effect/navigation nodes, `AnimatedSprite`, `TileMapNode`, UI controls and containers |
| `nexora.particles` | `Particle`, `ParticleConfig`, `ParticleSystem`, `ParticlePresets`, and particle modules |
| `nexora.physics` | `PhysicsWorld2D`, `get_physics_world`, `KinematicCollision2D`, `RayCastHit2D` |
| `nexora.rendering` | `Renderer`, `Camera`, `GPUContext`, `GPURenderer`, `GPUSpriteBatch`, `RenderSnapshot` |
| `nexora.rendering.gpu` | `GPUContext`, `WindowMode`, `GPUShader`, `GPUPipeline`, `GPUBuffer`, `GPUTexture`, `GPUSampler`, `GPURenderer`, `GPUSpriteBatch`, `RenderSnapshot` |
| `nexora.save` | `SaveManager`, `SaveGame`, `SaveMetadata`, save events/kinds/operations, and save errors |
| `nexora.scene` | `Scene`, `SceneState`, `SceneManager`, transitions, loading types, serializers, registries, and scene errors |
| `nexora.settings` | Engine, graphics, audio, layered, and base settings/store types |
| `nexora.signals` | `Signal`, `SignalConnection`, `EventBus` |
| `nexora.threading` | `ThreadContext`, `ThreadType`, `Future`, `FutureStatus`, `Task`, `TaskPriority`, `TaskStatus`, `TaskScheduler`, `SchedulerStats` |
| `nexora.tilemap` | `TileMap`, `TileSet`, `TileLayer`, chunks, projection, metadata, collision, animation, navigation, and avoidance types |
| `nexora.ui` | `UIInput` |

## 22. CLI and tests

After installation, the project exposes the `nexora` command:

~~~bash
nexora --help
~~~

Run the default test selection:

~~~bash
python -m pytest
~~~

The pytest configuration excludes hardware-dependent markers by default:

~~~bash
python -m pytest -m "not gpu and not audio"
~~~

Run audio or GPU tests explicitly only on a machine with the required SDL3
device/graphics backend:

~~~bash
python -m pytest -m audio
python -m pytest -m gpu
~~~

The GitHub Actions workflow currently runs Windows/Python 3.13 free-threaded
tests with `not gpu and not audio`.

## 23. Extension guidelines

- Build game code on `Game`, `Scene`, `Node`, and the high-level `Renderer`.
- Keep SDL3/GPU calls on the main thread.
- Use action input instead of hard-coding event handling where possible.
- Use `AssetManager` so textures, fonts, and sounds share caches.
- Keep save data as plain, bounded dictionaries and use your own signing key.
- Register scene/node serializers instead of reaching into private modules.
- Treat names beginning with an underscore and modules not re-exported in
  package `__init__` files as implementation details.

For API additions, update this file, add a focused test under `tests/`, and add
an example when the workflow is not obvious.
