<div align="center">

# Nexora Engine

**A Python 2D game engine powered by SDL3 and SDL_GPU.**

Scene graphs · ECS · GPU rendering · Isometric tilemaps · Navigation · UI

[![Tests](https://github.com/Lainupcomputer/Nexora/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Lainupcomputer/Nexora/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)
![SDL](https://img.shields.io/badge/Rendering-SDL3%20%2B%20SDL_GPU-blue)
![Free-Threading](https://img.shields.io/badge/Python-Free--Threading-blueviolet)
![Development](https://img.shields.io/badge/Status-Early%20Development-orange)

[Getting Started](#getting-started) · [Features](#features) · [Examples](#examples) · [Contributing](#contributing)

</div>

---

Nexora is a 2D game engine for **Python 3.13+**, built around **SDL3** and **SDL_GPU**.

It combines a scene and node workflow with a data-oriented ECS, GPU-accelerated rendering, orthogonal and isometric tilemaps, navigation, 2D physics, animation, audio, and a node-based UI framework.

Nexora is designed for Python's **free-threaded runtime**, with worker threads and scheduling infrastructure for parallel game logic.

> [!WARNING]
> Nexora is in early development. APIs, serialization formats, and internal systems may change. Examples and individual subsystems are evolving alongside the engine.

## Getting Started

### Requirements

- Python **3.13+**
- A **free-threaded Python build** to run with `-Xgil=0`
- SDL3 libraries accessible through PySDL3
- A graphics environment compatible with SDL_GPU for rendering examples

The current automated test workflow runs on **Windows with Python 3.13 free-threading**. It excludes GPU-marked tests.

### Install from source

```bash
git clone https://github.com/Lainupcomputer/Nexora.git
cd Nexora
python -m venv .venv
```

Activate the virtual environment in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the engine and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create the virtual environment using your free-threaded interpreter if you intend to use No-GIL mode.

### Run an example

From the repository root:

```bash
python -Xgil=0 examples/basic/hello_world.py
```

Check whether the GIL is disabled:

```bash
python -Xgil=0 -c "import sys; print(sys._is_gil_enabled())"
```

Expected output:

```text
False
```

### Minimal application

```python
from nexora import Game

game = Game(
    title="My Nexora Game",
    width=1280,
    height=720,
    target_fps=144,
)

game.run()
```

This creates a basic engine window. Explore the examples for scenes, sprites, input, UI, and gameplay systems.

## Features

### Core runtime

- Fixed and variable timestep updates
- Frame timing and interpolation
- Time scaling and unscaled time
- Engine initialization and shutdown lifecycle
- SDL3 event processing
- Resizable windows
- Windowed, borderless, and fullscreen modes
- VSync and graphics settings
- Persistent settings with reload and save workflows

### Threading and ECS

- Worker threads and task scheduling
- Task priorities, futures, and callbacks
- Thread-context and ownership checks
- Main-thread execution paths
- Entities, components, systems, and worlds
- Archetype-based component storage
- Queries and parallel queries
- Command buffers for structural changes
- System dependencies and execution ordering
- Read/write conflict detection

Nodes provide a hierarchical gameplay API, while the ECS supports data-oriented systems.

### Scenes and serialization

- Hierarchical node trees
- Local and world transforms
- Scene activation, unloading, pausing, and resuming
- Loading scenes and transition workflows
- Scene serialization and reconstruction
- Node type registration
- Serialization migrations
- Prefab saving and instantiation
- Prefab root overrides
- Serialized-scene integration with loading tasks

### Cameras

- Gameplay, follow, free, fixed, and cinematic camera workflows
- Position, zoom, and camera bounds
- Screen shake and trauma-based shake
- Punch effects
- Fades and flashes
- Letterboxing
- Scripted camera sequences

### GPU rendering

- SDL_GPU rendering backend
- Batched sprites
- Rectangles, shapes, and lines
- GPU text rendering and font atlases
- World-space and screen-space rendering
- Camera integration
- GPU textures, buffers, samplers, and pipelines
- Scissor clipping and nested UI clipping
- Render snapshots
- Post-processing framework and example effects

Post-processing examples include grayscale, vignette, chromatic aberration, film grain, scanlines, pixelation, distortion, and color tinting.

### Tilemaps and world interaction

- Orthogonal and isometric projections
- `TileMap`, `TileSet`, `TileLayer`, and `TileMapNode`
- Multiple tile layers
- Chunk-based storage and render caching
- Visible chunk selection
- Tile animations
- Tile metadata, tags, and custom properties
- World-to-tile and tile-to-world coordinate conversion
- Metadata queries at tile and world positions
- Solid-tile queries and collision helpers
- Tilemap serialization
- Asset-backed tileset textures
- Metadata-driven prefab spawning
- Enter-only teleport triggers
- Tracking and cleanup of spawned prefabs

### Navigation

- A* pathfinding through `TileNavigation`
- Walkability and traversal-cost queries
- Optional diagonal movement
- Dynamic blockers
- Path caching and invalidation
- Grid-space and world-space path queries
- `NavigationAgent2D` for character path following
- Target and waypoint tracking
- Desired direction and velocity helpers
- Path-changed, target-reached, and navigation-failed callbacks

`NavigationAgent2D` provides path-following information for character movement. Gameplay code can use its desired velocity together with the character's movement and collision logic.

### 2D physics

- `Body2D`
- `CharacterBody2D`
- `StaticBody2D`
- `Area2D`
- `CollisionShape2D`
- `RayCast2D`
- Collision layers and masks
- `move_and_slide` and `move_and_collide`
- Area overlap queries and callbacks
- Collision and raycast debug rendering

### Animation

- `AnimationFrame`, `AnimationClip`, and `AnimationSet`
- `Animator` and `AnimatedSprite`
- Arbitrary frame counts
- Per-frame durations
- Looping and non-looping clips
- Grid and row clip generation
- Runtime animation switching
- Frame-change callbacks

### Input

- Action-based keyboard and mouse input
- Multiple bindings per action
- Held, pressed, and released states
- Mouse position, movement, and wheel input
- Window focus handling
- SDL text input integration

### UI framework

- `UIRoot` and `UINode`
- Anchors, pivots, sizing, and positioning
- Responsive measure/arrange layout
- Mouse interaction, focus, and hover handling
- Text input
- Nested clipping and scroll-view culling

**Controls**

Buttons, checkboxes, radio buttons, dropdowns, sliders, text inputs, labels, and progress bars.

**Containers and feedback**

Panels, horizontal and vertical box containers, scroll views, list views, tooltips, and animated notifications.

### Audio

- Audio device and stream handling
- Audio buffers and caching
- Buses and channels
- Multiple sources and mixing
- Master, channel, and source volume controls
- Music playback and queueing
- Looping, pause, resume, and stop
- Listener support
- Music, SFX, ambient, and voice workflows

### Assets, settings, and save games

- Asset manager and loader registration
- Texture and font loading
- Asset caching, unloading, and reload workflows
- Graphics and audio settings
- Layered settings storage
- Manual saves, quick saves, and autosaves
- Save rotation
- Integrity checks and version handling
- Save/load events and notifications

## Examples

Run examples from the repository root so their asset paths resolve correctly.

| Example | Purpose |
| --- | --- |
| `examples/basic/hello_world.py` | Minimal engine window |
| `examples/basic/basic_game_structure.py` | Basic game organization |
| `examples/basic/input_example.py` | Input handling |
| `examples/basic/sprite_example.py` | Sprite rendering |
| `examples/basic/animated_sprite_idle.py` | Sprite animation |
| `examples/basic/isometric_tilemap_v2.py` | Isometric tilemap rendering |
| `examples/basic/scene_loading.py` | Scene loading |
| `examples/basic/scene_transition.py` | Scene transitions |
| `examples/basic/resizable_window.py` | Window resizing |
| `examples/basic/global_notifications.py` | Notifications |

Browse [`examples/`](examples/) for additional rendering, UI, audio, physics, and camera examples.

Some examples require specific assets or a working graphics/audio environment.

## Project Generator

Create a project directory:

```bash
nexora create MyNewGame
```

Choose a parent directory:

```bash
nexora create MyNewGame --path ./projects
```

The generator creates:

- `main.py`
- `README.md`
- `.gitignore`
- `assets/sprites/`
- `assets/audio/`
- `assets/fonts/`
- `scenes/`
- `scripts/`

> [!NOTE]
> The current generated `main.py` contains a placeholder.
> Replace it with the minimal application shown above before running the project.

## Tests and Continuous Integration

Run the default test suite:

```bash
python -Xgil=0 -m pytest
```

GPU-marked tests are excluded by the project's pytest configuration.

Run only GPU tests:

```bash
python -Xgil=0 -m pytest -m gpu
```

Run all tests, including GPU tests:

```bash
python -Xgil=0 -m pytest -m ""
```

GPU tests require a suitable graphics environment.

### GitHub Actions

The [Tests workflow](https://github.com/Lainupcomputer/Nexora/actions/workflows/tests.yml):

- Runs on pushes and pull requests
- Supports manual execution
- Uses a Windows runner
- Installs Python 3.13 free-threading
- Checks that No-GIL mode is active
- Runs tests excluding the `gpu` marker

The README test badge displays the workflow status for `main`. It does not represent GPU-test coverage or certification of every platform.

## Documentation

API documentation uses **Sphinx** with the **Furo** theme.

Install documentation dependencies:

```bash
python -m pip install -e ".[docs]"
```

Build the HTML documentation from the repository root:

```bash
python -m sphinx -b html docs/source docs/build/html
```

Open `docs/build/html/index.html` in your browser.

Documentation sources are available in [`docs/source/`](docs/source/).

## Development Direction

Current development focuses on making Nexora easier to use for complete games:

- Stabilizing public APIs and subsystem integration
- Improving project templates and onboarding
- Expanding practical gameplay examples
- Refining tilemap, navigation, and prefab workflows
- Improving asset and map authoring tools
- Keeping documentation aligned with implementation
- Extending automated validation
- Building a complete playable demonstration

Existing systems remain under active development; their presence does not imply a finalized API.

## Contributing

Nexora is developed by **Me**, who currently works full-time on the engine.

Contributions are welcome in areas such as:

- Engine and gameplay programming
- Bug reports and reproducible test cases
- Tests and regression coverage
- Documentation and tutorials
- Example projects
- Tooling and developer experience
- Pixel art, animation, and UI assets for demos

You do not need to contribute full-time.

For substantial architectural changes, open an issue first so the approach can be discussed before implementation.



Engine contributions and participation in the game's revenue-sharing arrangement are separate.

Interested? [Open an issue](https://github.com/Lainupcomputer/Nexora/issues) with your area of interest and links to relevant work.

## License

The repository's `LICENSE` file is currently a placeholder. Licensing terms have not yet been specified in that file.

Third-party dependencies and bundled assets may have their own licenses.