# Nexora Engine

**Nexora Engine** is a modern, experimental **2D game engine for Python**, built on **SDL3** and **SDL_GPU**.

It is designed around **Python 3.13 free-threading / No-GIL**, with parallel execution, GPU-accelerated rendering, a data-oriented ECS, a scene/node system, UI, audio, input management, and a clean modular architecture.

The goal of Nexora is to provide a capable 2D game engine while keeping game development accessible from Python.

> [!WARNING]
> **Nexora Engine is currently in early alpha development.**
>
> APIs, internal systems, project structure, and behavior may change significantly as development continues.
>
> Nexora is not yet recommended for production projects.

---

## Features

### Core

Nexora provides the core systems required to run real-time 2D applications and games.

* Engine lifecycle
* Game abstraction
* Fixed timestep updates
* Variable timestep updates
* Frame timing
* Frame interpolation
* Configurable target FPS
* Time scaling
* Window management
* Resizable windows
* Fullscreen support
* VSync support
* SDL3 integration

---

### Parallel Execution

Nexora is designed with **Python 3.13 free-threading / No-GIL** in mind.

Parallel execution is treated as a core engine feature rather than an optional layer added later.

Features include:

* Worker threads
* Task scheduler
* Priority-based task execution
* Futures
* Task cancellation
* Task callbacks
* Worker identification
* Thread context management
* Thread-safety checks
* Main-thread execution support
* Parallel CPU-bound workloads

When using a free-threaded Python build, Nexora can be run with:

```bash
python -Xgil=0 main.py
```

---

## Entity Component System

Nexora includes a data-oriented **Entity Component System** designed for scalable game logic and parallel execution.

Features include:

* Entities
* Components
* Systems
* Archetypes
* Archetype-based storage
* Command buffers
* System dependencies
* Automatic system conflict detection
* Parallel system execution
* Parallel archetype processing
* Fixed-update systems
* Render systems
* ECS scheduler

Example:

```python
from dataclasses import dataclass

from nexora.ecs import Component


@dataclass(slots=True)
class Position(Component):
    x: float = 0.0
    y: float = 0.0
```

The ECS is designed to work together with Nexora's threading system, allowing independent systems and workloads to execute in parallel where possible.

---

## GPU Rendering

Rendering in Nexora is built on **SDL_GPU** instead of SDL's traditional 2D renderer.

This gives Nexora direct access to modern GPU rendering concepts while keeping the engine portable through SDL3.

The rendering system currently includes:

* GPU context management
* Swapchain handling
* Graphics pipelines
* GPU buffers
* Shader management
* Texture management
* Samplers
* Sprite rendering
* Sprite batching
* Rectangle batching
* Shape batching
* Line batching
* Text rendering
* Font atlases
* Render snapshots
* Camera support
* VSync
* Window resizing

Nexora currently supports the graphics backends provided by SDL_GPU, depending on platform and SDL configuration.

Development is currently primarily tested using **Vulkan**.

---

## Text Rendering

Nexora includes its own GPU-accelerated text rendering system.

Fonts are rasterized into glyph atlases and rendered through the GPU renderer.

Features include:

* Font loading
* Glyph caching
* Font atlases
* GPU text rendering
* Text measurement
* Font metrics
* Dynamic glyph management

Example:

```python
font = text_system.font(
    "assets/fonts/Roboto-Regular.ttf",
    32,
)
```

---

## Scene System

Games can be organized using Nexora's scene and node architecture.

The scene system provides:

* Scenes
* Scene manager
* Node hierarchy
* Parent/child relationships
* Node transforms
* Scene activation
* Scene deactivation
* ECS integration
* UI integration

A scene acts as a container for the objects and systems required by a part of the game.

---

## UI Framework

Nexora contains a custom UI framework built directly on top of the engine's scene/node and GPU rendering systems.

Currently available UI components include:

* `UIRoot`
* `UINode`
* `Panel`
* `Label`
* `Button`
* `CheckBox`
* `RadioButton`
* `RadioButtonGroup`
* `Slider`
* `ProgressBar`
* `TextInput`
* `Dropdown`
* `ScrollView`
* `ListView`

The UI system supports concepts such as:

* Node-based UI hierarchy
* Mouse interaction
* Hover states
* Pressed states
* UI clipping
* Scrollable content
* Interactive controls
* Text input
* Selection controls

Example:

```python
from nexora.nodes import Button

button = Button(
    text="Start Game",
    width=220,
    height=50,
)
```

The UI framework is still under active development.

Planned improvements include:

* Focus management
* Keyboard navigation
* Layout containers
* Improved event propagation
* Themes and styling
* More advanced UI controls

---

## Input

Nexora provides an input abstraction on top of SDL3.

The input system currently supports:

* Keyboard input
* Mouse input
* Mouse buttons
* Mouse position
* Mouse movement delta
* Mouse wheel
* Pressed state
* Released state
* Held state
* Action bindings

Instead of directly checking physical keys everywhere, games can define logical actions.

Example:

```python
input_manager.bind(
    "move_left",
    "A",
)

input_manager.bind(
    "move_left",
    "LEFT",
)

input_manager.bind(
    "jump",
    "SPACE",
)
```

Game code can then work with actions instead of specific keys.

```python
if input_manager.action_down("move_left"):
    ...

if input_manager.action_pressed("jump"):
    ...
```

This keeps gameplay code independent from the actual input configuration.

---

## Audio

Nexora includes a custom audio subsystem built around SDL3 audio.

The current audio architecture includes:

* Audio system
* Audio device management
* Audio buffers
* PCM audio
* WAV loading
* Sound effects
* Music playback
* Audio channels
* Audio mixer
* Audio buses
* Audio sources
* Audio listeners
* Audio caching
* Spatial audio foundations

Major audio components include:

```text
AudioSystem
AudioDevice
AudioBuffer
AudioMixer
AudioBus
AudioChannel
AudioPlayer
MusicPlayer
Sound
AudioSource
AudioListener
AudioCache
```

The audio system is designed so that sound effects, music, buses, sources, and listeners can later be integrated directly with scenes and gameplay systems.

---

## Asset Management

Nexora contains a growing asset management system for loading and managing game resources.

Current functionality includes:

* Asset abstraction
* Asset loaders
* Asset manager
* Texture loading
* Audio asset integration
* Asset caching foundations

The asset system is still under development.

Future work is expected to include:

* Asset handles
* Asset registry
* Asynchronous loading
* Dependency tracking
* Reference management
* Asset unloading
* Hot reloading

---

## Command Line Interface

Installing Nexora also provides the `nexora` command.

New game projects can be created using:

```bash
nexora create MyGame
```

The generated project structure includes directories for common game resources and code.

Example:

```text
MyGame/
├── assets/
│   ├── audio/
│   ├── fonts/
│   └── sprites/
├── scenes/
├── scripts/
├── main.py
├── README.md
└── .gitignore
```

The project generator is still under development and will be expanded as Nexora's public game API stabilizes.

---

## Project Structure

The engine itself is organized into independent subsystems.

```text
nexora/
├── assets/
├── audio/
├── cli/
├── core/
├── ecs/
├── input/
├── nodes/
├── rendering/
│   └── gpu/
├── scene/
└── threading/
```

The architecture intentionally keeps engine systems separated so they can evolve independently.

---

## Installation

### Requirements

Nexora currently targets:

* Python 3.13+
* SDL3
* PySDL3
* A GPU/backend supported by SDL_GPU

Clone the repository:

```bash
git clone https://github.com/Lainupcomputer/Nexora.git
cd Nexora
```

Create a virtual environment:

### Windows

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install Nexora in editable mode:

```bash
pip install -e .
```

For development dependencies:

```bash
pip install -e ".[dev]"
```

---

## Running with Free-Threading

Nexora is designed to take advantage of Python's free-threaded execution mode.

You can verify the GIL state with:

```bash
python -Xgil=0 -c "import sys; print(sys._is_gil_enabled())"
```

A free-threaded runtime should report:

```text
False
```

Nexora applications can then be started with:

```bash
python -Xgil=0 main.py
```

> [!NOTE]
> Nexora can contain systems that must remain on the main thread, especially functionality interacting directly with SDL or GPU resources.
>
> The engine's threading architecture is designed to distinguish these workloads from tasks that can safely execute in parallel.

---

## Development

Install the development dependencies:

```bash
pip install -e ".[dev]"
```

Run the normal test suite:

```bash
pytest
```

GPU-dependent tests are marked separately because they require SDL3, a windowing environment, and compatible GPU hardware.

They can be executed explicitly when required.

---

## Tests

Nexora contains automated tests covering multiple engine systems, including:

* Core game loop
* Nodes
* Scenes
* Scene manager
* Assets
* Audio
* Rendering
* GPU text measurement
* UI nodes
* UI root
* Panels
* Labels
* Buttons
* UI input

GPU tests are separated from normal unit tests where possible.

The test suite will continue to grow as the public engine API stabilizes.

---

## Documentation

Project documentation is maintained alongside the engine source.

Documentation can be rebuilt locally during development.

The documentation is still evolving together with the engine API and may occasionally lag behind the latest development branch.

---

# Roadmap

Nexora is under active development.

The roadmap below represents the current direction and is not a strict release schedule.

## Core

* [x] Engine lifecycle
* [x] Game loop
* [x] Fixed timestep
* [x] Variable timestep
* [x] Frame interpolation
* [x] Time scaling
* [x] Window management
* [x] Resizable windows
* [x] Fullscreen support
* [x] VSync

## Threading

* [x] Worker threads
* [x] Task scheduler
* [x] Futures
* [x] Task priorities
* [x] Task cancellation
* [x] Main-thread execution
* [x] Free-threading / No-GIL architecture
* [ ] Additional profiling and diagnostics

## ECS

* [x] Entities
* [x] Components
* [x] Systems
* [x] Archetypes
* [x] Command buffers
* [x] System scheduler
* [x] System dependencies
* [x] Conflict detection
* [x] Parallel system execution
* [ ] Additional performance profiling
* [ ] ECS debugging tools

## Rendering

* [x] SDL_GPU rendering
* [x] GPU context
* [x] Graphics pipelines
* [x] GPU buffers
* [x] Shaders
* [x] Textures
* [x] Samplers
* [x] Sprite rendering
* [x] Sprite batching
* [x] Rectangle batching
* [x] Shape rendering
* [x] Line rendering
* [x] GPU text rendering
* [x] Font atlas
* [x] Camera support
* [ ] Sprite animation
* [ ] Particle system
* [ ] Render targets
* [ ] Post-processing
* [ ] Lighting

## Scene System

* [x] Nodes
* [x] Node hierarchy
* [x] Scenes
* [x] Scene manager
* [x] Scene lifecycle foundations
* [x] ECS integration
* [ ] Scene serialization
* [ ] Scene files
* [ ] Prefabs
* [ ] Extended node lifecycle

## UI

* [x] UI node system
* [x] UI root
* [x] Panels
* [x] Labels
* [x] Buttons
* [x] Check boxes
* [x] Radio buttons
* [x] Sliders
* [x] Progress bars
* [x] Text input
* [x] Dropdowns
* [x] Scroll views
* [x] List views
* [ ] Focus management
* [ ] Keyboard navigation
* [ ] Layout containers
* [ ] UI themes
* [ ] Extended styling system
* [ ] Additional widgets

## Input

* [x] Keyboard
* [x] Mouse
* [x] Mouse wheel
* [x] Input states
* [x] Action bindings
* [ ] Gamepad support
* [ ] Controller mapping
* [ ] Input rebinding
* [ ] Input contexts

## Audio

* [x] Audio device management
* [x] PCM audio
* [x] WAV loading
* [x] Sound playback
* [x] Audio buffers
* [x] Audio cache
* [x] Audio channels
* [x] Audio mixer
* [x] Audio buses
* [x] Music playback
* [x] Audio sources
* [x] Audio listener
* [x] Spatial audio foundations
* [ ] Additional audio formats
* [ ] Streaming improvements
* [ ] Audio effects
* [ ] Advanced spatial audio

## Assets

* [x] Asset abstraction
* [x] Asset loaders
* [x] Asset manager
* [x] Basic caching
* [ ] Asset handles
* [ ] Asset registry
* [ ] Async loading
* [ ] Dependency tracking
* [ ] Hot reload
* [ ] Automatic unloading

## Gameplay

* [ ] Sprite animation system
* [ ] Animation state machines
* [ ] Tweening
* [ ] Tilemaps
* [ ] Collision detection
* [ ] Physics
* [ ] Navigation
* [ ] Particle system
* [ ] Object pooling
* [ ] Coroutines
* [ ] Save system

## Tooling

* [x] Basic project CLI
* [x] Project generator
* [ ] Complete generated starter project
* [ ] Asset tools
* [ ] Profiler
* [ ] Debug overlay
* [ ] Scene editor
* [ ] Asset browser
* [ ] Inspector

---

# Current Development Status

Nexora is currently in **early alpha**.

The fundamental engine architecture is already in place:

```text
Core
 ↓
Threading
 ↓
ECS
 ↓
Scene / Nodes
 ↓
Rendering + Input + Audio
 ↓
UI + Assets
```

Current development is increasingly focused on turning these low-level systems into a convenient game-development workflow.

Major upcoming areas include:

1. Completing the UI framework
2. Improving the project generator
3. Sprite animation
4. Tilemaps
5. Collision and physics
6. Gameplay-oriented APIs
7. Integration testing through real Nexora games

Building small real games with Nexora will be used to identify missing APIs and validate the engine architecture.

---

# Design Goals

Nexora aims to follow a few core principles.

### Python First

Game code should remain readable and feel natural to Python developers.

### Modern GPU Rendering

Rendering should use modern GPU APIs through SDL_GPU instead of relying on legacy software-style rendering abstractions.

### Parallel by Design

Parallel execution should be part of the engine architecture from the beginning rather than being added as an optimization later.

### Modular Architecture

Rendering, audio, ECS, input, scenes, assets, and threading should remain clearly separated engine systems.

### Low Boilerplate

Common game-development tasks should require as little setup code as reasonably possible.

### Build Real Games

Engine features should ultimately be driven by real game requirements rather than existing only as isolated technical demonstrations.

---

# Contributing

Nexora is currently evolving quickly.

Contributions, experiments, bug reports, and technical discussions are welcome, but contributors should expect APIs to change while the engine is in alpha.

When contributing:

* Keep systems modular
* Avoid unnecessary dependencies
* Add tests where practical
* Keep SDL/GPU thread restrictions in mind
* Prefer explicit APIs over hidden global state
* Preserve compatibility with Python free-threading where possible

---

# License

See [`LICENSE`](LICENSE) for license information.

---

# Status

**Nexora Engine — Early Alpha**

Built with:

* Python 3.13+
* SDL3
* SDL_GPU
* PySDL3

Designed for modern, GPU-accelerated and parallel 2D game development in Python.
