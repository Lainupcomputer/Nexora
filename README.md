# Nexora Engine

**Nexora Engine** is a modern 2D game engine for Python, designed around **Python 3.13 free-threading (No-GIL)** and a low-level **SDL3 + Vulkan rendering backend**.

The engine focuses on GPU-accelerated rendering, parallel game logic, data-oriented architecture, low boilerplate, and a clean modular design while keeping game development accessible to Python developers.

> ⚠️ **Nexora Engine is currently in early development.**
>
> APIs, rendering systems, scene architecture, and internal implementation details may still change significantly.

---

## ✨ Features

### Core Engine

Nexora provides the foundation required to create and run games:

* Engine lifecycle management
* Variable timestep updates
* Fixed timestep updates
* Frame timing
* Configurable target FPS
* Time scaling
* Frame interpolation
* Automatic window handling
* Resizable windows
* Fullscreen support
* VSync support
* Main-thread management
* Engine shutdown handling
* Central game lifecycle

The game loop separates normal updates, fixed updates, rendering, input processing, and engine events.

---

## ⚡ Python 3.13 Free-Threading

Nexora is designed specifically around **Python 3.13 free-threading / No-GIL**.

Parallel execution is treated as an important part of the engine architecture rather than an optional add-on.

The engine includes its own threading infrastructure with:

* Worker threads
* Priority-based task scheduling
* Futures
* Task cancellation
* Task callbacks
* Task statistics
* Worker identification
* Thread-safety checks
* Main-thread execution support
* Controlled worker synchronization

CPU-heavy workloads can be moved away from the main thread while SDL3, windowing, and GPU operations remain inside their required thread boundaries.

When using a free-threaded Python build, Nexora can be started with:

```bash
python -Xgil=0
```

---

# 🧩 Entity Component System

Nexora includes a data-oriented **Entity Component System (ECS)** designed with parallel processing in mind.

The ECS currently includes:

* Entities
* Components
* Systems
* Archetypes
* Archetype-based storage
* Chunk-based processing
* Parallel chunk processing
* System dependencies
* System scheduling
* System conflict detection
* Parallel system execution
* Command buffers
* Fixed-update systems
* Render systems

Built-in example components include:

* `Transform`
* `Velocity`
* `Sprite`
* `Health`

The ECS is designed to allow independent workloads to execute concurrently while keeping structural changes controlled.

---

# 🌳 Scene & Node System

Nexora now includes a hierarchical **Scene / Node system** built on top of the ECS.

Scenes provide the hierarchical structure and lifetime management of game objects, while ECS provides the underlying data and processing architecture.

Example hierarchy:

```text
MainScene
├── World
│   └── Tilemap
│       ├── Ground
│       ├── Decoration
│       └── Collision
├── Player
├── Enemies
├── Camera
└── UI
```

The current Scene system provides:

* `Scene`
* `Node`
* Hierarchical parent/child relationships
* Scene root nodes
* Scene node creation
* Node lookup
* Node removal
* Node destruction
* ECS entity integration
* ECS `Transform` integration
* Local transforms
* World position
* World rotation
* World scale
* Combined world transforms
* Scene update forwarding
* Fixed-update forwarding
* Render forwarding

Example:

```python
from nexora.scene import Scene

scene = Scene("MainScene")

world = scene.create_node("World")
player = scene.create_node("Player", parent=world)
weapon = scene.create_node("Weapon", parent=player)

player.transform.x = 100.0
weapon.transform.x = 50.0
weapon.transform.rotation = 45.0
```

Nodes are backed by ECS entities, allowing the scene hierarchy and ECS architecture to work together without maintaining a separate object system.

---

# 🎬 Scene Manager

Nexora includes a `SceneManager` for managing multiple loaded scenes.

It currently supports:

* Loading scenes
* Unloading scenes
* Activating scenes
* Retrieving scenes
* Checking whether a scene is loaded
* Clearing all scenes
* Tracking the active scene

Example:

```python
scene = Scene("MainMenu")

game.scenes.load(scene)
game.scenes.activate("MainMenu")
```

The scene system is intended to support game states such as:

```text
Scenes/
├── MainMenu
├── Settings
├── CharacterSelect
├── Game
├── PauseMenu
└── GameOver
```

The future editor architecture will build on top of this scene hierarchy.

---

# 🎮 Input

Nexora provides an action-oriented input system instead of requiring games to manually process SDL events.

Actions provide state information such as:

* Down
* Pressed
* Released

Bindings can be configured using readable action names:

```python
self.input.bind("left", "A")
self.input.bind("right", "D")
self.input.bind("jump", "SPACE")
self.input.bind("escape", "ESCAPE")
```

Gameplay code can then query the action:

```python
if self.input.action("jump").pressed:
    player.jump()
```

Mouse input includes:

* Position
* Movement delta
* Button state
* Press/release detection
* Mouse wheel

The input system remains independent from individual gameplay systems.

---

# 🖥️ Rendering

Nexora's renderer is based on **SDL3 + Vulkan**.

Rendering is GPU-based rather than relying on CPU-side `pygame.Surface` drawing.

Current rendering functionality includes:

* Vulkan GPU context
* Vulkan swapchain
* SDL3 window integration
* GPU-based 2D rendering
* Rectangles
* Circles
* Lines
* Polygons
* Pixels
* Sprites
* GPU textures
* Text rendering
* World-space rendering
* Screen-space rendering
* Camera transformations
* Frame interpolation

The renderer is designed as a low-level GPU backend on top of which higher-level rendering systems can be built.

Rendering operations that interact with SDL3, window, and GPU resources are kept within the required main-thread boundaries.

---

# 🖼️ GPU Textures & Sprites

Nexora supports GPU textures that can be created from loaded image data.

A basic rendering flow looks like:

```python
image = self.assets.load_texture("demo_sprite.png")

texture = GPUTexture(
    self.engine.gpu_context.device,
    image.width,
    image.height,
    data=image.pixels,
    bytes_per_pixel=image.bytes_per_pixel,
)

self.renderer.sprite(
    texture,
    x,
    y,
    width=image.width,
    height=image.height,
)
```

Sprites support properties including:

* Position
* Width
* Height
* Rotation
* Scaling

The sprite renderer is already usable for basic 2D game rendering.

More advanced batching and resource management are planned for later development.

---

# 🔤 GPU Text Rendering

Nexora includes a dedicated GPU text-rendering path.

The current text renderer integrates:

* SDL3
* SDL3_ttf
* Vulkan
* GPU texture resources
* Text image generation
* GPU rendering

Text is converted into GPU-compatible image data and rendered through the Vulkan pipeline.

The text renderer is being developed separately from the higher-level 2D rendering API so that it can eventually participate efficiently in the same GPU rendering pipeline as other graphical objects.

---

# 📷 Camera

Nexora includes a camera system for world/screen coordinate transformations.

Current functionality includes:

* World-to-screen conversion
* Screen-to-world conversion
* Zoom
* Zoom limits
* Camera following
* Dead zones
* World bounds
* Camera shake
* Smooth movement

Example:

```python
camera.follow(
    player_x,
    player_y,
    smooth=0.12,
    delta_time=delta_time,
)

camera.set_zoom(1.5)

camera.shake(25.0, 0.5)
```

The renderer uses world coordinates and applies the camera transformation before presenting the final image.

---

# 🔊 Audio

Nexora includes a basic audio subsystem for game audio playback.

The current audio architecture includes:

* Audio player
* Audio playback
* Audio caching
* Sound loading
* Playback state management
* Audio updates integrated into the main game loop

Example:

```python
sound = self.assets.load_sound("jump.wav")
self.audio.player.play(sound)
```

Audio is currently functional but remains less mature than the rendering and ECS systems.

More advanced features such as mixing, music management, spatial audio, and effects are planned for later development.

---

# 📦 Asset System

Nexora includes an asset-loading layer used by the engine and examples.

The current asset functionality includes loading resources such as:

* Textures
* Sounds

Assets can be loaded through the game's asset interface:

```python
image = self.assets.load_texture("demo_sprite.png")
```

The asset system is currently being expanded toward a more complete resource management architecture.

Planned improvements include stronger caching, lifecycle management, and additional asset types.

---

# 🧵 Threading Model

Nexora separates work according to its thread requirements.

```text
                         Nexora Engine
                              │
              ┌───────────────┴───────────────┐
              │                               │
         Main Thread                    Worker Threads
              │                               │
       ┌──────┼──────┐                 ┌──────┼──────┐
       │      │      │                 │      │      │
     Window  Input  Vulkan             ECS   Tasks  Loading
                    Rendering
```

The main thread is responsible for operations that require SDL3, window, or GPU context access.

Worker threads are intended for CPU-heavy workloads such as:

* ECS processing
* Gameplay calculations
* Pathfinding
* Procedural generation
* Asset preparation
* Data processing
* Background tasks

The goal is to keep the main thread responsive while making use of available CPU cores.

---

# 🧱 Architecture

Nexora is split into independent subsystems rather than being implemented as one monolithic engine.

The current architecture is centered around:

```text
Nexora
│
├── Core
│   ├── Engine
│   ├── Game
│   ├── Game Loop
│   ├── Time
│   └── Configuration
│
├── Threading
│   ├── Scheduler
│   ├── Workers
│   ├── Tasks
│   ├── Futures
│   └── Context
│
├── Window
│   ├── SDL3 Window
│   └── Viewport
│
├── Rendering
│   ├── Vulkan
│   ├── GPU Context
│   ├── Renderer
│   ├── GPU Textures
│   ├── Text Renderer
│   └── Camera
│
├── Input
│   ├── Actions
│   ├── Bindings
│   └── Mouse Input
│
├── Audio
│   ├── Audio Player
│   └── Audio Cache
│
├── Assets
│   └── Asset Loading
│
├── Scene
│   ├── Scene
│   ├── Node
│   └── Scene Manager
│
├── ECS
│   ├── Entities
│   ├── Components
│   ├── Systems
│   ├── Archetypes
│   ├── Chunks
│   ├── Scheduler
│   └── Commands
│
└── Debug
    └── Logging
```

The architecture intentionally separates:

**Scene hierarchy**

from

**ECS data and processing**

and from

**GPU rendering**.

This allows the individual systems to evolve independently.

---

# 🚧 Roadmap

Nexora is actively being developed.

### Core

* [x] Engine lifecycle
* [x] Variable timestep
* [x] Fixed timestep
* [x] Frame timing
* [x] Target FPS
* [x] Time scaling
* [x] Frame interpolation
* [x] Window management
* [x] Resizable windows
* [x] Fullscreen support

### Input

* [x] Keyboard input
* [x] Action bindings
* [x] Pressed / released / down states
* [x] Mouse input
* [x] Mouse wheel

### Rendering

* [x] SDL3 window integration
* [x] Vulkan context
* [x] Swapchain
* [x] GPU rendering
* [x] 2D primitives
* [x] GPU textures
* [x] Sprite rendering
* [x] Camera
* [x] GPU text rendering
* [ ] Advanced batching
* [ ] Sprite batching
* [ ] Texture atlases
* [ ] Render command batching
* [ ] Advanced GPU resource management

### ECS

* [x] Entities
* [x] Components
* [x] Systems
* [x] Archetypes
* [x] Chunk processing
* [x] Parallel ECS processing
* [x] System scheduling
* [x] System dependencies
* [x] Conflict detection
* [x] Command buffers
* [x] Fixed-update systems
* [x] Render systems

### Scene

* [x] Scene
* [x] Node hierarchy
* [x] Parent / child relationships
* [x] ECS entity integration
* [x] Transform integration
* [x] World transforms
* [x] SceneManager
* [x] Scene activation
* [x] Scene destruction
* [ ] Advanced node API
* [ ] Node lifecycle callbacks
* [ ] Scene serialization
* [ ] Scene file format
* [ ] Editor integration

### Assets

* [x] Texture loading
* [x] Sound loading
* [ ] Complete asset manager
* [ ] Advanced caching
* [ ] Asset lifecycle management
* [ ] Additional asset types
* [ ] Resource dependency management

### Audio

* [x] Basic sound playback
* [x] Audio cache
* [x] Game-loop audio updates
* [ ] Music management
* [ ] Audio mixing
* [ ] Spatial audio
* [ ] Audio effects

### Gameplay Systems

* [ ] Animation system
* [ ] Particle system
* [ ] Tweening
* [ ] Object pooling
* [ ] Coroutines
* [ ] Game state management
* [ ] Loading screens

### UI & Tools

* [ ] UI framework
* [ ] Debug console
* [ ] Debug overlay
* [ ] Profiler
* [ ] Inspector
* [ ] Settings system
* [ ] Localization
* [ ] Save system
* [ ] Replay system
* [ ] Hot reload
* [ ] Plugin system
* [ ] Nexora Editor

The roadmap will evolve as the engine architecture matures.

---

# 📦 Requirements

Nexora currently targets:

* **Python 3.13**
* **Python free-threaded / No-GIL build**
* **SDL3**
* **SDL3_ttf**
* **Vulkan-capable GPU and driver**

Development is currently focused primarily on **Windows**.

Linux support is expected to become more important as the engine matures.

---

# 🔧 Installation

Clone the repository:

```bash
git clone git@github.com:Lainupcomputer/Nexora.git
cd Nexora
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install Nexora:

```powershell
pip install -e .
```

---

# 🚀 Running Nexora

Nexora contains examples and tests for the individual engine systems.

Because the engine is designed around Python's free-threaded runtime, development and test programs should be started with:

```powershell
python -Xgil=0 ...
```

For example:

```powershell
python -Xgil=0 examples\scene_example.py
```

The Scene example demonstrates:

* Scene creation
* Node hierarchy
* Parent/child relationships
* ECS-backed transforms
* World transforms
* Sprite rendering
* Player movement
* Rotation
* Scaling

Other examples demonstrate individual engine subsystems.

---

# 🧪 Testing

Nexora contains tests for individual engine subsystems.

Current test coverage includes areas such as:

* Core engine behavior
* Game loop
* Timing
* Thread scheduler
* Futures
* Task cancellation
* Task callbacks
* Task priorities
* Parallel CPU workloads
* ECS
* Archetypes
* Parallel ECS processing
* System scheduling
* Input
* Rendering
* GPU text rendering
* Camera transformations
* Scene
* Node
* SceneManager
* Game/Scene integration
* Game loop / Scene integration
* Audio

Tests are executed using the free-threaded Python runtime:

```powershell
python -Xgil=0 tests\test_node.py
```

For example, the current Scene and Node tests verify:

```text
Node tests
    7 / 7 passed

Scene tests
    12 / 12 passed

Game / Scene tests
    8 / 8 passed

Game Loop / Scene tests
    5 / 5 passed
```

GPU rendering tests can be executed with:

```powershell
python -Xgil=0 tests\test_text_renderer.py
```

The parallel execution tests are particularly important because they verify that CPU-bound workloads can execute concurrently under Python's free-threaded runtime.

---

# 🎯 Design Goals

Nexora is built around several core principles.

### Performance

Use data-oriented structures, GPU acceleration, parallel execution, caching, and efficient update paths where they provide real benefits.

### Parallel by Design

Multithreading should not be something developers have to manually bolt onto every game.

Nexora should make parallel workloads a natural part of game development.

### GPU First

Rendering should make use of the GPU rather than relying on CPU-side drawing wherever possible.

The Vulkan backend provides the foundation for a scalable modern rendering pipeline.

### Low Boilerplate

Creating a game should require as little engine-specific code as possible.

### Safe Thread Boundaries

SDL3, windowing, and graphics operations must respect their thread requirements while CPU-heavy workloads can run concurrently on worker threads.

### Modular Architecture

Engine systems should remain independent enough to evolve without turning Nexora into a monolithic framework.

### Python First

Nexora aims to combine Python's simplicity and flexibility with modern GPU rendering and parallel execution.

---

# 📌 Current Status

Nexora is currently **experimental and under active development**.

The engine already has working foundations for:

* Core engine lifecycle
* Variable and fixed game updates
* Frame timing
* Frame interpolation
* Python 3.13 free-threaded execution
* Worker thread scheduler
* Futures
* ECS
* Archetypes
* Parallel ECS processing
* System scheduling
* Input
* SDL3 window handling
* Vulkan rendering
* GPU textures
* Sprite rendering
* GPU text rendering
* Camera system
* Basic audio playback
* Asset loading
* Scene / Node hierarchy
* ECS-backed transforms
* Scene management
* Automated tests

The **Scene / Node system is currently being expanded**, while the rendering and ECS architecture remain important areas of development.

The engine should currently be considered **experimental** and the API is **not yet stable**.

---

# 📄 License

See [`LICENSE`](LICENSE) for license information.

---

# 🌐 Repository

**GitHub:**

[github.com/Lainupcomputer/Nexora](https://github.com/Lainupcomputer/Nexora)
