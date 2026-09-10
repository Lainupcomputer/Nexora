# Nexora Engine

**Nexora Engine** is a modern 2D game engine for Python, designed around **Python 3.13 free-threading (No-GIL)** and a low-level **SDL3 + Vulkan rendering backend**.

The engine focuses on performance, parallel game logic, GPU-accelerated rendering, low boilerplate, and a clean modular architecture while keeping game development accessible to Python developers.

> ⚠️ **Nexora Engine is currently in early development.**
> APIs, rendering systems, and internal architecture may change significantly as development continues.

---

## ✨ Features

### Core Engine

Nexora provides the foundation required to build and run a game:

* Engine lifecycle management
* Fixed timestep game loop
* Variable timestep updates
* Frame timing
* Configurable target FPS
* Time scaling
* Automatic window handling
* Resizable windows
* Fullscreen support
* VSync support
* Main-thread management
* Engine shutdown handling

---

## ⚡ Free-Threading & Parallel Execution

Nexora is designed specifically around **Python 3.13 free-threading / No-GIL**.

Instead of treating Python threading as an optional feature, parallel execution is part of the engine architecture.

Current threading infrastructure includes:

* Real worker threads
* Priority-based task scheduler
* Parallel CPU-bound workloads
* Futures
* Task cancellation
* Task callbacks
* Task statistics
* Worker identification
* Thread-safety checks
* Main-thread execution support
* Controlled worker synchronization

Nexora is intended to make parallel game logic a first-class engine feature.

The engine can be launched using:

```bash
python -Xgil=0
```

when using a Python build that supports free-threaded execution.

---

## 🧩 Entity Component System

Nexora includes a data-oriented **Entity Component System (ECS)** designed with parallel processing in mind.

Current ECS architecture includes:

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

The ECS is designed to allow independent workloads to execute concurrently while maintaining controlled structural changes.

---

## 🎮 Input

Nexora provides an action-oriented input API instead of requiring games to manually process every SDL event.

Example:

```python
input.is_down("move_left")
input.is_pressed("jump")
input.is_released("fire")
```

Bindings can be configured using readable names:

```python
input.bind("move_left", "A")
input.bind("move_left", "LEFT")
input.bind("jump", "SPACE")
input.bind("shoot", "MOUSE_LEFT")
```

Mouse input includes:

* Position
* Movement delta
* Button state
* Press/release detection
* Mouse wheel

The input system is designed to remain independent from individual gameplay systems.

---

# 🖥️ Rendering

Nexora's rendering architecture has moved away from `pygame-ce` and is now based on **SDL3 + Vulkan**.

The renderer is designed as a GPU-based rendering backend rather than relying on CPU-side surface drawing.

Current rendering work includes:

* Vulkan GPU context
* Vulkan swapchain
* GPU-based 2D rendering
* Window/surface integration through SDL3
* Rectangles
* Circles
* Lines
* Polygons
* Pixels
* Text rendering
* World-space rendering
* Screen-space rendering
* Camera transformations
* GPU text rendering

Rendering operations that interact with SDL3/window resources are explicitly controlled around the engine's main-thread requirements.

The rendering backend is still under active development and will continue to evolve toward a more complete batching and GPU rendering pipeline.

---

## 🔤 GPU Text Rendering

Nexora includes a dedicated GPU text-rendering path.

The current text renderer integrates:

* SDL3
* SDL_ttf
* Vulkan
* GPU texture resources
* Text image generation
* GPU rendering

The renderer is being developed separately from the higher-level 2D rendering API so that text can eventually participate efficiently in the same GPU rendering pipeline as other graphical objects.

---

## 📷 Camera

The camera system provides world/screen coordinate transformations and smooth camera movement.

Current functionality includes:

* World-to-screen conversion
* Screen-to-world conversion
* Smooth zoom
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

Nexora uses a world coordinate system where the camera defines how world coordinates are transformed into the final screen representation.

---

# 🧵 Threading Model

Nexora separates work according to its thread requirements.

```text
                         Nexora Engine
                              │
              ┌───────────────┴───────────────┐
              │                               │
         Main Thread                     Worker Threads
              │                               │
       ┌──────┼──────┐                 ┌──────┼──────┐
       │      │      │                 │      │      │
     Window  Input  Vulkan            ECS    Tasks  Loading
       │      │    Rendering           │      │      │
       │      │      │                 │      │      │
       └──────┴──────┘                 └──────┴──────┘
```

The main thread is responsible for operations that require SDL3/window/Vulkan context access.

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

Nexora is split into independent subsystems instead of being implemented as one monolithic engine.

The architecture currently revolves around:

```text
Nexora
│
├── Core
│   ├── Engine
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
│   ├── Renderer
│   ├── Text Renderer
│   └── Camera
│
├── Input
│   ├── Actions
│   └── Bindings
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

---

# 🚧 Planned Features

Nexora is actively being developed.

Planned systems include:

* [ ] Asset Manager
* [ ] Texture loading and caching
* [ ] Sprite rendering
* [ ] Sprite batching
* [ ] Sprite sheets
* [ ] Animation system
* [ ] Audio system
* [ ] Particle system
* [ ] Tweening
* [ ] UI framework
* [ ] Debug console
* [ ] Debug overlay
* [ ] Profiler
* [ ] Save system
* [ ] Localization
* [ ] Settings system
* [ ] Replay system
* [ ] Object pooling
* [ ] Game state management
* [ ] Loading screens
* [ ] Coroutines
* [ ] Plugin system
* [ ] Inspector
* [ ] Hot reload
* [ ] Advanced Vulkan rendering pipeline
* [ ] GPU sprite batching
* [ ] Texture atlases
* [ ] Render command batching
* [ ] Improved GPU resource management

This list will evolve as development progresses.

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

Install the engine:

```powershell
pip install -e .
```

---

# 🚀 Running Nexora

Nexora currently contains examples and tests for individual engine systems.

Because the engine makes use of Python's free-threaded runtime, development and test programs should be started with:

```powershell
python -Xgil=0 ...
```

For example:

```powershell
python -Xgil=0 tests\test_text_renderer.py
```

The text renderer test initializes:

* SDL3
* Vulkan
* A GPU rendering context
* The swapchain
* SDL_ttf
* The Nexora GPU text renderer

and renders text through the GPU pipeline.

---

# 🧪 Testing

Nexora contains automated tests for the individual engine subsystems.

Tests currently cover areas such as:

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
* Rendering
* GPU text rendering
* Camera transformations

Example:

```powershell
python -Xgil=0 tests\test_scheduler_t.py
```

GPU rendering tests can be executed using:

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
* Game loop
* Timing
* Python 3.13 free-threaded execution
* Worker thread scheduler
* Futures
* ECS
* Archetypes
* Parallel ECS processing
* System scheduling
* Input
* SDL3 window handling
* Vulkan rendering foundation
* GPU text rendering
* Camera system
* Automated tests

The rendering backend is currently one of the most actively developed parts of the engine.

The API should be considered **unstable** until Nexora reaches a more mature stage.

---

# 📄 License

See [`LICENSE`](LICENSE) for license information.

---

# 🌐 Repository

**GitHub:**

[github.com/Lainupcomputer/Nexora](https://github.com/Lainupcomputer/Nexora?utm_source=chatgpt.com)
