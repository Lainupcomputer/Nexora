# Nexora Engine
[![Tests](https://github.com/Lainupcomputer/Nexora/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Lainupcomputer/Nexora/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)
![Runtime](https://img.shields.io/badge/Runtime-Free--Threading-blueviolet)
![Status](https://img.shields.io/badge/Status-Early%20Development-orange)

**Nexora Engine** is a modern 2D game engine for Python, built on **SDL3** and **SDL_GPU** and designed for **Python 3.13 free-threading / No-GIL**.

It combines a scene and node workflow with a data-oriented ECS, GPU-accelerated rendering, tilemaps, 2D physics, animation, audio, UI, asset management, save games, and a growing collection of runnable examples.

> [!WARNING]
> Nexora is in early development. Public APIs and internal structure may still change before the first stable release.

---

## Highlights

- **SDL3 + SDL_GPU** renderer with batched sprites, shapes, lines, rectangles, and GPU text
- **Scene graph and ECS** that can be used together
- **Parallel execution** designed around Python 3.13 free-threading
- **2D physics** with bodies, collision shapes, areas, raycasts, layers/masks, and debug rendering
- **Tilemaps** with layers, chunks, render caching, collision helpers, and node integration
- **Node-based UI** with responsive layout, controls, scrolling, clipping, tooltips, and notifications
- **Audio mixer** with buses, sources, music queueing, volume control, and caching
- **Save manager** with quick/manual/automatic saves, integrity checks, and global notifications
- **Examples, tests, benchmarks, Sphinx documentation, and a project CLI**

---

## Requirements

- Python **3.13+**  
  For free-threading, use a compatible free-threaded Python build.
- SDL3 / PySDL3
- A GPU backend supported by SDL_GPU

Install Nexora for local development:

```bash
pip install -e .
pip install -e ".[dev]"
```

Optional documentation dependencies:

```bash
pip install -e ".[docs]"
```

Run an example with free-threading enabled:

```bash
python -Xgil=0 examples/example.py
```

Verify the GIL state:

```bash
python -Xgil=0 -c "import sys; print(sys._is_gil_enabled())"
```

Expected output on a compatible build:

```text
False
```

---

## Core Runtime

Nexora provides the runtime systems required by a 2D game:

- Fixed and variable timestep updates
- Frame interpolation
- Centralized time, unscaled time, time scaling, and frame counters
- Engine lifecycle and clean shutdown
- SDL3 event processing
- Resizable windows
- Windowed, borderless, and fullscreen modes
- VSync control
- Settings storage with defaults, reload, reset, and autosave

---

## Threading and ECS

Nexora is designed to benefit from Python 3.13 free-threading while keeping ownership rules explicit.

### Threading

- Worker threads and task scheduling
- Priorities, futures, callbacks, and cancellation
- Worker identification and task statistics
- Thread-safety checks
- Main-thread-only execution paths
- Parallel CPU workloads

### Entity Component System

- Entities, components, systems, and worlds
- Archetype and chunk-based storage
- Queries and parallel queries
- Command buffers for structural changes
- Fixed-update and render systems
- Priorities and explicit dependencies
- Automatic read/write conflict detection
- Parallel system execution

The ECS can power data-heavy gameplay while nodes remain the ergonomic API for game code.

---

## Scenes, Nodes, and Cameras

The scene system supplies a hierarchical gameplay workflow:

- Parent/child node trees
- Local and world transforms
- Position, rotation, scale, enabled state, and visibility
- Recursive update, fixed update, render, and cleanup
- Scene load, activate, unload, clear, pause, and resume lifecycle
- Scene loading and transition examples
- ECS/world integration

Available camera workflows include gameplay, follow, fixed, free, and cinematic cameras.

Camera effects include shake, trauma shake, punch, fades, flashes, letterboxing, and scripted sequences.

---

## GPU Rendering

Nexora renders through **SDL_GPU** rather than a software renderer.

### High-level rendering

- `Renderer`
- `SpriteBatch` and `BatchSprite`
- Rectangle, shape, and line rendering
- World-space and screen-space rendering
- Camera integration
- Sprite caching and batching statistics

### GPU layer

- `GPUContext`
- GPU textures, buffers, samplers, shaders, and graphics pipelines
- Sprite, rectangle, shape, line, and text batches
- GPU font atlases and glyph caching
- Render snapshots
- GPU scissor clipping for sprites and text
- Nested clip rectangles for UI rendering

### Post-processing

The post-processing framework already includes example effects for:

- Grayscale
- Vignette
- Chromatic aberration
- Film grain and scanlines
- Pixelation
- Distortion
- Color tint
- Low-health visual treatment

---

## UI Framework

The node-based UI framework integrates directly with scenes and the renderer.

### Foundation

- `UIRoot` and `UINode`
- Anchors, pivots, sizing, positioning, visibility, and input states
- Responsive measure/arrange layout
- Mouse interaction, focus, hover, and text input
- UI clipping and ScrollView culling

### Controls

- `Button`
- `CheckBox`
- `Dropdown`
- `RadioButton` and `RadioButtonGroup`
- `Slider`
- `TextInput`
- `Label`
- `ProgressBar`

### Containers and output

- `Panel`
- `BoxContainer`, `VBoxContainer`, and `HBoxContainer`
- `ScrollView`
- `ListView`
- `Tooltip`
- Animated `NotificationCenter` with info, success, warning, and error states

---

## Input

Input is action-based, so gameplay code does not need to depend directly on SDL events.

```python
input.bind("move_left", "A")
input.bind("move_left", "LEFT")

if input.is_down("move_left"):
    ...
```

Supported input features include:

- Keyboard and mouse buttons
- Mouse position, delta, and wheel
- Held, pressed, and released states
- Multiple bindings per action
- Window focus handling
- SDL text input lifecycle

---

## Animation

The animation system keeps frame timing and state separate from rendering.

- `AnimationFrame`
- `AnimationClip`
- `AnimationSet`
- `Animator`
- `AnimatedSprite`
- Arbitrary frame counts
- Per-frame durations
- Looping and non-looping clips
- Grid and row clip generation
- Runtime clip switching
- Frame-change callbacks

---

## Tilemaps

Nexora includes a tilemap system intended for larger 2D worlds.

- `TileMap`, `TileSet`, `TileLayer`, and `TileMapNode`
- Multi-layer maps
- Chunk-based storage
- Chunk render caching and dirty tracking
- Visible chunk bounds
- Batched tile rendering
- Tile metadata, tags, and custom properties
- Solid-tile queries and AABB movement helpers
- Tile collision results for character movement

---

## 2D Physics

Nexora includes a node-oriented 2D physics layer.

- `Body2D`
- `CharacterBody2D`
- `StaticBody2D`
- `Area2D`
- `CollisionShape2D`
- `RayCast2D`
- Collision layers and masks
- `move_and_slide` and `move_and_collide`
- Area overlap queries and entered/exited callbacks
- Collision and raycast debug visualization

---

## Audio

The audio subsystem is integrated into the engine lifecycle.

- Audio device and stream handling
- `AudioBuffer` and cache management
- Audio buses/channels and effective volume control
- Sources and multi-source mixing
- Music playback and queueing
- Looping, pause/resume, stop, and cleanup
- Listener support
- Music, SFX, ambient, voice, and master volume workflows

---

## Assets and Save Games

### Assets

- `AssetManager`
- Loader registration
- Texture and font loading
- Path resolution and normalized cache keys
- Load status tracking
- Asset lookup, unload, cache clearing, and shutdown

### Save games

- `SaveManager`
- Manual, quick, and automatic save/load operations
- Save events and notifications
- Integrity validation
- Version and invalid-data errors
- Restricted deserialization safeguards

---

## Project Creation

Create a starter project with the CLI:

```bash
nexora new MyGame
```

The generator is still evolving, but provides the initial project structure for a Nexora game.

---

## Tests and Examples

Run the standard test suite:

```bash
pytest
```

GPU tests are excluded by default:

```bash
pytest -m gpu
```

Run all tests:

```bash
pytest -m ""
```

The `examples/` directory demonstrates rendering, UI, audio, animation, tilemaps, scene loading, save games, camera effects, post-processing, physics, raycasts, and debugging.

---

## Documentation

Nexora uses **Sphinx** for API documentation. Build the docs locally using the repository's Sphinx configuration after installing the `docs` extras.

---

## Roadmap

The core feature set is in place. Current work is focused on making it easier to build complete games with Nexora:

- Scene/prefab serialization and reusable game-object workflows
- Asset import pipeline for game resources
- Tilemap tooling and external map workflow
- Expanded gameplay examples and a complete vertical-slice demo
- Gamepad support and input rebinding
- Further physics shapes and gameplay-specific collision helpers
- Stable public API boundaries
- Automated CI, packaging, releases, and a future PyPI workflow

---

## Design Goals

- **Pythonic API:** readable game code with low boilerplate
- **Performance:** GPU batching, data-oriented ECS, and parallel execution
- **Free-threading:** designed for modern Python without assuming the GIL
- **Modularity:** rendering, ECS, scenes, UI, audio, animation, input, physics, and tilemaps remain separable
- **Escape hatches:** advanced users can access lower-level systems when needed

---

## Contributing

Nexora is under active development. Bug reports, tests, examples, documentation improvements, and implementation feedback are welcome.

Because the API is still evolving, please discuss larger architectural changes before implementation.

---

## License

See [LICENSE](LICENSE) for license information.
