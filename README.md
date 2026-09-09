# Nexora Engine

**Nexora Engine** is a modern 2D game engine for Python, built around `pygame-ce` and designed to take advantage of **Python 3.13 free-threading (No-GIL)**.

The engine focuses on performance, parallel game logic, low boilerplate, and a clean architecture while keeping game development accessible to Python developers.

> ⚠️ **Nexora Engine is currently in early development.**
> APIs and internal systems may change significantly as development continues.

---

## ✨ Features

### Core

* Fixed timestep game loop
* Variable timestep updates
* Frame timing and interpolation
* Configurable target FPS
* Time scaling
* Automatic window handling
* Resizable windows
* Fullscreen support
* VSync support
* Clean engine lifecycle

### ⚡ Parallel Execution

Nexora is designed specifically for **Python 3.13 free-threading / No-GIL**.

* Real worker threads
* Priority-based task scheduler
* Parallel CPU-bound workloads
* Futures
* Task cancellation
* Task callbacks
* Task statistics
* Worker thread identification
* Thread-safety checks
* Dedicated main-thread execution for systems that require it

The goal is to make parallel game logic a first-class part of the engine rather than an afterthought.

### 🧩 Entity Component System

Nexora includes a data-oriented ECS architecture.

* Entities
* Components
* Systems
* Archetypes
* Chunk-based storage
* Parallel chunk processing
* System dependencies
* Automatic system conflict detection
* Parallel system execution
* Command buffers for structural changes
* Fixed-update systems
* Render systems

### 🎮 Input

The input system provides an action-based API instead of requiring games to directly process every Pygame event.

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

Mouse support includes:

* Position
* Movement delta
* Button state
* Press/release detection
* Mouse wheel

### 🖥️ Rendering

The current renderer provides basic 2D drawing functionality:

* Rectangles
* Circles
* Lines
* Polygons
* Pixels
* Text
* Surface blitting
* World-space rendering
* Screen-space rendering
* Camera transformations

Rendering operations are explicitly restricted to the main thread where required by SDL/Pygame.

### 📷 Camera

The camera system currently supports:

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

---

## 🚧 Planned Features

Nexora is actively being developed. Planned systems include:

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
* [ ] Improved rendering pipeline

This list will evolve as development progresses.

---

## 🧵 Threading Model

Nexora separates operations based on their thread requirements.

```text
                    Nexora Engine
                         │
             ┌───────────┴───────────┐
             │                       │
        Main Thread             Worker Threads
             │                       │
      ┌──────┼──────┐          ┌─────┼─────┐
      │      │      │          │     │     │
    Window Input Rendering    ECS   Tasks  Loading
      │      │      │          │     │     │
      └──────┴──────┘          └─────┴─────┘
```

The main thread handles operations that require Pygame/SDL access, while CPU-heavy work can be distributed across worker threads.

Nexora is designed to run with:

```bash
python -Xgil=0
```

This enables Python's free-threaded execution mode where supported.

---

## 📦 Requirements

Currently:

* Python **3.13 free-threading build**
* `pygame-ce`

Nexora is currently being developed and tested primarily on Windows.

---

## 🔧 Installation

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

Install dependencies:

```bash
pip install -e .
```

---

## 🚀 Running an Example

Nexora currently includes example programs demonstrating individual engine systems.

For example:

```powershell
python -Xgil=0 examples\camera_example.py
```

The camera example demonstrates:

* Player movement
* Camera following
* Dead zones
* Smooth zoom
* World boundaries
* Camera shake
* World rendering

---

## 📁 Project Structure

```text
Nexora Engine/
│
├── nexora/
│   ├── core/
│   │   ├── engine.py
│   │   ├── game_loop.py
│   │   ├── time.py
│   │   └── config.py
│   │
│   ├── threading/
│   │   ├── scheduler.py
│   │   ├── worker.py
│   │   ├── future.py
│   │   ├── task.py
│   │   └── context.py
│   │
│   ├── window/
│   │   ├── window.py
│   │   └── viewport.py
│   │
│   ├── rendering/
│   │   ├── renderer.py
│   │   └── camera.py
│   │
│   ├── input/
│   │   ├── input.py
│   │   ├── action.py
│   │   └── bindings.py
│   │
│   ├── ecs/
│   │   ├── entity.py
│   │   ├── component.py
│   │   ├── system.py
│   │   ├── world.py
│   │   ├── archetype.py
│   │   ├── archetype_world.py
│   │   ├── parallel.py
│   │   ├── scheduler.py
│   │   └── commands.py
│   │
│   └── debug/
│       └── logger.py
│
├── examples/
├── tests/
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 🧪 Testing

Nexora includes tests for its core systems.

The test suite is designed to verify both functionality and the engine's parallel execution model.

For example:

```powershell
python -Xgil=0 tests\test_scheduler_t.py
```

The scheduler tests verify:

* Basic task execution
* Future states
* Cancellation
* Exceptions
* Callbacks
* Waiting for tasks
* Task priorities
* Parallel CPU workloads
* Pending task cancellation
* Scheduler statistics

Parallel CPU tests are specifically used to verify that worker threads can execute CPU-bound workloads concurrently when running in free-threaded Python.

---

## 🎯 Design Goals

Nexora is built around a few core principles:

### Performance

Use data-oriented structures, parallel execution, caching, and efficient update paths where they provide real benefits.

### Parallel by Design

Threading should not be something developers have to manually bolt onto every game.

### Low Boilerplate

Creating a game should require as little engine-specific code as possible.

### Safe Main-Thread Boundaries

Systems that interact with Pygame/SDL should remain on the main thread while CPU-heavy work can run in parallel.

### Modular Architecture

Engine systems should be independent enough to evolve without turning the entire engine into one large monolithic framework.

### Python First

Nexora is intended to make high-performance 2D game development possible while retaining Python's simplicity and flexibility.

---

## 📌 Current Status

Nexora is currently **experimental and under active development**.

The engine already has working foundations for:

* Core engine lifecycle
* Game loop
* Timing
* No-GIL worker scheduler
* Futures
* ECS
* Archetypes
* Parallel ECS processing
* System scheduling
* Input
* Rendering
* Camera system
* Automated tests

The API should be considered unstable until the engine reaches a more mature stage.

---

## 📄 License

See [`LICENSE`](LICENSE) for license information.

---

## 🌐 Repository

**GitHub:**
https://github.com/Lainupcomputer/Nexora
