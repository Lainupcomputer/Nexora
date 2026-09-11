from __future__ import annotations

from nexora import Game
from nexora.scene import Scene
from nexora.ecs.system import System
from nexora.core.game_loop import GameLoop


def test_game_loop_scene_integration():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    scene = Scene("TestScene")
    game.scene = scene

    assert game.scene is scene


def test_scene_fixed_update_through_game():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    scene = Scene("TestScene")
    game.scene = scene

    class TestSystem(System):
        def __init__(self):
            self.calls = 0
            self.delta = None

        def fixed_update(self, world, fixed_delta_time):
            self.calls += 1
            self.delta = fixed_delta_time

    system = TestSystem()
    scene.world.add_system(system)

    scene.fixed_update(0.02)

    assert system.calls == 1
    assert system.delta == 0.02


def test_scene_render_through_game():
    game = Game(
        title="Scene Test",
        width=320,
        height=240,
        target_fps=60,
    )

    scene = Scene("TestScene")
    game.scene = scene

    calls = []

    class TestSystem(System):
        def render(self, world, interpolation):
            calls.append(interpolation)

    system = TestSystem()
    scene.world.add_system(system)

    scene.render(0.5)

    assert calls == [0.5]


# ==============================================================
# GameLoop integration
# ==============================================================


class FakeInput:
    def initialize(self):
        pass

    def begin_frame(self, events):
        pass

    def end_frame(self):
        pass


class FakeRenderer:
    def begin_frame(self):
        return True

    def end_frame(self):
        pass


class FakeGPUContext:
    def __init__(self):
        self.calls = 0

    def poll_events(self):
        self.calls += 1
        return []


class FakeAudioPlayer:
    def update(self):
        pass


class FakeAudio:
    def __init__(self):
        self.player = FakeAudioPlayer()


class FakeScene:
    def __init__(self):
        self.fixed_updates = []
        self.renders = []

    def fixed_update(self, delta_time):
        self.fixed_updates.append(delta_time)

    def render(self, interpolation):
        self.renders.append(interpolation)


class FakeGame:
    def __init__(self):
        self.scene = FakeScene()
        self.updates = []
        self.fixed_updates = []
        self.render_calls = 0

    def update(self, delta_time):
        self.updates.append(delta_time)

    def fixed_update(self, fixed_delta_time):
        self.fixed_updates.append(fixed_delta_time)
        self.scene.fixed_update(fixed_delta_time)

    def handle_event(self, event):
        pass

    def render(self, interpolation):
        self.render_calls += 1
        self.scene.render(interpolation)


class FakeEngine:
    def __init__(self):
        self.game = FakeGame()
        self.input = FakeInput()
        self.renderer = FakeRenderer()
        self.gpu_context = FakeGPUContext()
        self.audio = FakeAudio()


def test_game_loop_runs_scene_fixed_update():
    engine = FakeEngine()

    loop = GameLoop(
        engine,
        target_fps=0,
        fixed_delta_time=1.0 / 60.0,
    )

    original_fixed_update = engine.game.fixed_update

    def fixed_update_once(fixed_delta_time):
        original_fixed_update(fixed_delta_time)
        loop.stop()

    engine.game.fixed_update = fixed_update_once

    loop.run()

    assert len(engine.game.fixed_updates) == 1
    assert len(engine.game.scene.fixed_updates) == 1
    assert (
        engine.game.fixed_updates[0]
        == 1.0 / 60.0
    )
    assert (
        engine.game.scene.fixed_updates[0]
        == 1.0 / 60.0
    )

def test_game_loop_runs_scene_render_with_interpolation():
    engine = FakeEngine()

    loop = GameLoop(
        engine,
        target_fps=0,
        fixed_delta_time=1.0 / 60.0,
    )

    original_end_frame = engine.renderer.end_frame

    def end_frame_once():
        original_end_frame()
        loop.stop()

    engine.renderer.end_frame = end_frame_once

    loop.run()

    assert engine.game.render_calls == 1
    assert len(engine.game.scene.renders) == 1

    interpolation = engine.game.scene.renders[0]

    assert 0.0 <= interpolation < 1.0

    