# Nexora Engine

**Nexora Engine** is a modern 2D game engine for Python, built on **SDL3** and **SDL_GPU** and designed with **Python 3.13 free-threading / No-GIL** in mind.

Nexora combines a traditional scene and node architecture with a data-oriented ECS, GPU-accelerated rendering, parallel execution, tilemaps, animation, audio, input handling, and a growing UI framework.

The goal is to provide a clean and Pythonic game-development API without hiding the lower-level systems required for performance and flexibility.

> [!WARNING]
> **Nexora Engine is currently in early development.**
>
> APIs, internal systems, and project structure may change significantly before a stable release.

---

## Features

### Core

Nexora provides the fundamental runtime systems required by a game engine.

- Fixed timestep game loop
- Variable timestep updates
- Frame interpolation
- Centralized time system
- Delta time and unscaled delta time
- Time scaling
- Fixed update accumulator
- Frame and fixed-frame counters
- Configurable target FPS
- Engine lifecycle management
- SDL3 event processing
- Window resize handling
- Fullscreen and borderless modes
- VSync support
- Settings system

---

## Parallel Execution

Nexora is designed around **Python 3.13 free-threading / No-GIL**.

The threading system provides:

- Real worker threads
- Priority-based task scheduling
- Futures
- Task cancellation
- Task callbacks
- Worker identification
- Task statistics
- Thread-safety checks
- Main-thread-only execution
- Parallel CPU workloads

The goal is to make parallel game logic a first-class engine feature instead of an optional layer added later.

---

## Entity Component System

Nexora contains a data-oriented ECS designed to work alongside the scene and node system.

Features include:

- Entities
- Components
- Systems
- Worlds
- Archetypes
- Chunk-based storage
- Queries
- Parallel queries
- Command buffers
- Structural changes
- Fixed-update systems
- Render systems
- System priorities
- Explicit system dependencies
- Automatic read/write conflict detection
- Parallel system execution
- Main-thread-only systems

Nodes can internally use ECS entities and components while exposing a convenient object-oriented API to game code.

---

## Scene and Node System

Nexora provides a hierarchical scene graph built around `Scene` and `Node`.

Nodes support:

- Parent/child hierarchies
- Local transforms
- World transforms
- Position
- Rotation
- Scale
- Visibility
- Enabled state
- Recursive updates
- Fixed updates
- Recursive rendering
- Automatic cleanup
- ECS integration

Example:

```python
from nexora.scene import Scene
from nexora.nodes import Node


class MainScene(Scene):

    def on_enter(self) -> None:
        player = Node(
            "Player",
            self.world,
        )

        player.position = (
            100.0,
            100.0,
        )

        self.root.add_child(
            player
        )
```

The base `Node` already provides the common 2D transform functionality, avoiding unnecessary intermediate node types.

---

## Cameras

Nexora provides several camera nodes for different gameplay requirements.

Available cameras include:

- `Camera2D`
- `FollowCamera2D`
- `FreeCamera2D`
- `FixedCamera2D`
- `CinematicCamera2D`

These can be used for normal gameplay cameras, player tracking, scripted sequences, fixed viewpoints, and free camera movement.

---

## GPU Rendering

Rendering is built around **SDL_GPU** rather than a traditional software or SDL renderer.

Nexora provides both high-level rendering APIs and lower-level GPU abstractions.

### High-Level Rendering

- `Renderer`
- `SpriteBatch`
- `BatchSprite`
- Camera integration
- Rectangle rendering
- Shape rendering
- Line rendering
- Text rendering

### Low-Level GPU Layer

- `GPUContext`
- `GPURenderer`
- GPU buffers
- GPU textures
- Samplers
- Shaders
- Graphics pipelines
- Sprite batching
- Rectangle batching
- Shape batching
- Line batching
- Text rendering
- Font atlases
- Render snapshots

The separation allows normal game code to use simple rendering APIs while still allowing advanced systems to access the GPU layer directly.

---

## Shaders

Nexora contains its own shader pipeline for SDL_GPU.

Shader assets currently include support for the engine's rendering systems and are compiled for supported GPU backends.

The renderer architecture is designed to support additional shaders and rendering effects as the engine develops.

---

## Post-Processing

Nexora includes a post-processing framework for applying effects to rendered scenes.

The system provides a foundation for effects such as:

- Screen effects
- Color manipulation
- Scene transitions
- Custom shader-based effects

Post-processing support is still evolving and should currently be considered experimental.

---

## Text Rendering

Nexora contains a GPU-accelerated text system based on SDL_ttf.

Features include:

- Font loading
- Glyph caching
- Font atlases
- GPU text rendering
- Configurable font sizes
- Reusable font resources

Fonts are handled through the engine's `TextSystem`.

---

## Sprite Animation

Nexora includes a dedicated animation system separated from rendering.

Core animation types include:

- `AnimationFrame`
- `AnimationClip`
- `AnimationSet`
- `Animator`
- `AnimatedSprite`

Animations support:

- Arbitrary frame counts
- Per-frame durations
- Looping animations
- Non-looping animations
- Multiple named clips
- Animation sets
- Runtime clip switching
- Frame progression
- Remaining frame-time preservation

Animation data is kept separate from the `AnimatedSprite` node so animation logic can evolve independently of rendering.

---

## Tilemaps

Nexora contains a dedicated tilemap system suitable for larger 2D worlds.

The tilemap architecture includes:

- `TileMap`
- `TileSet`
- `TileLayer`
- `TileChunk`
- `TileChunkCache`
- Tile metadata
- Tile collision
- `TileMapNode`

Features include:

- Multiple layers
- Chunk-based maps
- Chunk caching
- Tile metadata
- Collision information
- Scene/node integration

The chunk-based architecture is designed to support larger maps without requiring the entire world to be processed every frame.

---

## Character Movement

Nexora includes `CharacterBody2D` as a foundation for gameplay-oriented character movement.

It integrates with the node and world systems and provides a basis for collision-aware movement.

This system is still evolving alongside the collision and tilemap APIs.

---

## Input

Nexora provides an action-based input system on top of SDL3.

Instead of coupling gameplay code directly to SDL events, controls can be mapped to named actions.

Example:

```python
input.bind(
    "move_left",
    "A",
)

input.bind(
    "move_left",
    "LEFT",
)

input.bind(
    "jump",
    "SPACE",
)
```

Game code can then use:

```python
if input.is_down("move_left"):
    ...

if input.is_pressed("jump"):
    ...

if input.is_released("fire"):
    ...
```

Input support includes:

- Keyboard
- Mouse buttons
- Mouse position
- Mouse movement delta
- Mouse wheel
- Action bindings
- Multiple bindings per action
- Pressed state
- Released state
- Held state
- Window focus handling

---

## Audio

Nexora contains an audio subsystem integrated into the engine lifecycle.

The current audio architecture provides a foundation for:

- Audio resource management
- Playback
- Runtime audio updates
- Engine-managed audio lifecycle

The audio API is still under active development.

---

# UI System

Nexora contains a node-based UI framework designed to integrate directly with scenes.

## UI Foundation

- `UIRoot`
- `UINode`
- Anchors
- Pivots
- Positioning
- Sizing
- Interaction states
- Visibility
- Hierarchical UI
- Mouse interaction

---

## UI Controls

Currently available controls include:

- `Button`
- `CheckBox`
- `Dropdown`
- `RadioButton`
- `RadioButtonGroup`
- `Slider`
- `TextInput`

---

## UI Containers

Layout and container nodes include:

- `Panel`
- `BoxContainer`
- `VBoxContainer`
- `HBoxContainer`
- `ScrollView`
- `ListView`

These provide the foundation for building menus, inventories, settings screens, lists, and HUD layouts.

---

## UI Output

Output-oriented UI nodes currently include:

- `Label`
- `ProgressBar`
- `Tooltip`
- `NotificationCenter`

`NotificationCenter` supports multiple notification types and screen anchors.

`Tooltip` provides contextual information for UI elements.

---

## Assets

Nexora contains an asset-management layer for loading and reusing game resources.

The system is designed to avoid unnecessary resource duplication and provide centralized resource management.

Asset handling will continue to expand as additional resource types are added.

---

# Basic Architecture

A simplified overview of the current architecture:

```text
                         Nexora
                            │
              ┌─────────────┼─────────────┐
              │             │             │
             Core         Runtime       Gameplay
              │             │             │
         ┌────┼────┐    ┌───┼────┐   ┌────┼─────┐
         │    │    │    │   │    │   │    │     │
       Engine Loop Time  GPU Input Audio Anim Tilemap
              │
              │
             ECS
              │
              │
           Scene Graph
              │
             Node
              │
      ┌────────┼─────────┬──────────┐
      │        │         │          │
    Camera   Entity    Texture     World
                                    │
                                  TileMap

                           UI
                            │
                ┌───────────┼───────────┐
                │           │           │
             Controls   Containers    Output
```

The scene graph provides an ergonomic gameplay API while ECS and GPU systems handle lower-level data and rendering workloads.

---

# Installation

Nexora currently requires:

- Python 3.13+
- SDL3
- PySDL3

Install the project in editable mode during development:

```bash
pip install -e .
```

Install development dependencies:

```bash
pip install -e ".[dev]"
```

---

# Running with Free-Threading

Nexora is designed with Python's free-threaded execution in mind.

Run an example using:

```bash
python -Xgil=0 examples/example.py
```

You can verify the GIL state with:

```bash
python -Xgil=0 -c "import sys; print(sys._is_gil_enabled())"
```

Expected output on a compatible free-threaded Python build:

```text
False
```

---

# Running Tests

Run the standard test suite:

```bash
pytest
```

GPU-dependent tests are marked separately and excluded from the normal test run.

Run GPU tests explicitly with:

```bash
pytest -m gpu
```

Run all tests:

```bash
pytest -m ""
```

---

# Examples

The `examples/` directory contains runnable demonstrations for many engine systems.

Examples cover areas such as:

- Rendering
- Text
- Input
- Audio
- Scenes
- Nodes
- UI controls
- UI containers
- Notifications
- Tooltips
- Animation
- Tilemaps

Examples are especially useful while APIs are still evolving.

---

# Project Creation

Nexora includes a command-line interface intended to create basic project structures.

```bash
nexora new MyGame
```

> [!NOTE]
> The project generator is still experimental and may change before the first stable release.

---

# Documentation

Nexora uses **Sphinx** for generated API documentation.

Build the documentation locally from the project tools or Sphinx configuration.

Generated documentation should not be committed to the source tree unless explicitly required for deployment.

---

# Development Status

Nexora is currently an **early-stage engine**.

Many core systems already exist, but APIs should not yet be considered stable.

### Implemented / Active

- [x] SDL3 engine lifecycle
- [x] SDL_GPU rendering
- [x] Fixed timestep
- [x] Variable timestep
- [x] Centralized time system
- [x] Time scaling
- [x] Input system
- [x] Mouse support
- [x] Window resizing
- [x] Fullscreen support
- [x] VSync
- [x] Scene system
- [x] Node hierarchy
- [x] 2D transforms
- [x] Camera nodes
- [x] ECS
- [x] Archetypes
- [x] Parallel ECS scheduling
- [x] Worker thread system
- [x] GPU sprite batching
- [x] GPU shape rendering
- [x] GPU text rendering
- [x] Font atlases
- [x] Sprite animation
- [x] Animated sprites
- [x] Tilemaps
- [x] Tilemap chunking
- [x] Tile metadata
- [x] Tile collision foundations
- [x] CharacterBody2D
- [x] Audio foundations
- [x] UI system
- [x] UI controls
- [x] Layout containers
- [x] Scroll views
- [x] List views
- [x] Tooltips
- [x] Notifications
- [x] Post-processing foundation
- [x] Sphinx documentation
- [x] CLI foundation

### Planned / In Progress

- [ ] GPU scissor / clip rectangles
- [ ] True ScrollView rendering clipping
- [ ] Expanded collision system
- [ ] Physics integration
- [ ] Improved tilemap rendering and tooling
- [ ] Improved animation tooling
- [ ] Expanded audio system
- [ ] Scene transitions
- [ ] Resource import pipeline
- [ ] Serialization
- [ ] Prefabs / reusable scene objects
- [ ] Improved project generator
- [ ] Stable public API
- [ ] Packaging and PyPI release workflow
- [ ] Performance profiling and benchmarks

---

# Design Goals

Nexora aims to provide:

### Pythonic APIs

Game code should remain readable and concise without exposing unnecessary SDL or GPU boilerplate.

### Performance

Performance-sensitive systems use batching, ECS data layouts, GPU rendering, and parallel execution where appropriate.

### Free-Threading

Nexora is designed to take advantage of modern free-threaded Python instead of assuming the traditional GIL execution model.

### Modular Architecture

Rendering, ECS, scenes, nodes, UI, animation, audio, input, and tilemaps remain separate systems with clearly defined responsibilities.

### Low Boilerplate

Creating a game should require as little engine setup code as practical.

### Escape Hatches

Advanced developers should still be able to access lower-level GPU, ECS, and runtime systems when necessary.

---

# Contributing

Nexora is currently under heavy development.

Bug reports, experiments, tests, documentation improvements, and implementation feedback are welcome.

Because APIs are still evolving, large changes should be discussed before implementation.

---

# License

See the `LICENSE` file for license information.