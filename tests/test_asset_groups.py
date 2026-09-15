from __future__ import annotations

from pathlib import Path

import pytest

from nexora.assets.group import AssetGroupDefinition


class FakeStage:
    def __init__(self, name, status, callback=None, update=None):
        self.name = name
        self.status = status
        self.callback = callback
        self.update_callback = update
        self.progress = 0.0


class FakeTask:
    def __init__(self):
        self.stages = []

    def add_stage(self, name, *, weight=1.0, status=None, callback=None, update=None):
        stage = FakeStage(name, status or name, callback=callback, update=update)
        self.stages.append(stage)
        return stage


def test_group_definition_normalizes_name_and_fonts():
    group = AssetGroupDefinition.create(
        " HQ ",
        fonts=[("fonts/ui.ttf", 24)],
        sounds=["audio/hq.wav"],
        textures=["world/hq.png"],
    )

    assert group.name == "hq"
    assert group.fonts[0].size == 24.0
    assert group.sounds == ("audio/hq.wav",)
    assert group.textures == ("world/hq.png",)


def test_persistent_group_rejects_dependencies():
    with pytest.raises(ValueError):
        AssetGroupDefinition.create(
            "core",
            dependencies=["ui"],
            persistent=True,
        )


def test_register_and_lookup_group(monkeypatch):
    from nexora.assets.manager import AssetManager

    # Avoid SDL text-system setup in this focused group bookkeeping test.
    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")

    group = manager.register_group(
        "beach",
        sounds=["audio/waves.wav"],
        textures=["world/beach.png"],
    )

    assert group.name == "beach"
    assert manager.get_group("BEACH") is group
    assert manager.group_names() == ("beach",)
    assert not manager.is_group_loaded("beach")


def test_dependency_deltas_include_shared_dependency(monkeypatch):
    from nexora.assets.manager import AssetManager

    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")
    manager.register_group("shared")
    manager.register_group("a", dependencies=["shared"])
    manager.register_group("b", dependencies=["shared"])
    manager.register_group("world", dependencies=["a", "b"])

    deltas = manager._group_acquire_deltas("world")

    assert deltas["world"] == 1
    assert deltas["a"] == 1
    assert deltas["b"] == 1
    assert deltas["shared"] == 2


def test_dependency_cycle_is_rejected(monkeypatch):
    from nexora.assets.manager import AssetManager

    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")
    manager.register_group("a", dependencies=["b"])
    manager.register_group("b", dependencies=["a"])

    with pytest.raises(ValueError, match="dependency cycle"):
        manager._group_acquire_deltas("a")


def test_collect_group_assets_deduplicates_shared_resources(monkeypatch):
    from nexora.assets.manager import AssetManager

    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")
    a = manager.register_group(
        "a",
        fonts=[("fonts/ui.ttf", 24)],
        sounds=["audio/click.wav"],
        textures=["ui/common.png"],
    )
    b = manager.register_group(
        "b",
        fonts=[("fonts/ui.ttf", 24)],
        sounds=["audio/click.wav"],
        textures=["ui/common.png"],
    )

    fonts, sounds, textures = manager._collect_group_assets([a, b])

    assert len(fonts) == 1
    assert sounds == ["audio/click.wav"]
    assert textures == ["ui/common.png"]


def test_load_group_uses_font_audio_texture_order(monkeypatch):
    from nexora.assets.manager import AssetManager

    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")
    manager.register_group(
        "hq",
        fonts=[("fonts/ui.ttf", 24)],
        sounds=["audio/hq.wav"],
        textures=["world/hq.png"],
    )

    calls = []
    monkeypatch.setattr(manager, "font", lambda path, size, force_reload=False: calls.append(("font", str(path))))
    monkeypatch.setattr(manager, "sound", lambda path, force_reload=False: calls.append(("audio", str(path))))
    monkeypatch.setattr(manager, "texture", lambda path, force_reload=False: calls.append(("texture", str(path))))

    manager.load_group("hq")

    assert [kind for kind, _ in calls] == ["font", "audio", "texture"]
    assert manager.group_ref_count("hq") == 1


def test_shared_asset_reference_survives_until_last_group(monkeypatch):
    from nexora.assets.manager import AssetManager

    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")
    manager.register_group("a", textures=["shared.png"])
    manager.register_group("b", textures=["shared.png"])

    monkeypatch.setattr(manager, "texture", lambda path, force_reload=False: object())
    unloaded = []
    monkeypatch.setattr(
        manager,
        "unload_texture",
        lambda path, unload_image=False: unloaded.append(Path(path).name) or True,
    )

    manager.load_group("a")
    manager.load_group("b")

    manager.unload_group("a")
    assert unloaded == []

    manager.unload_group("b")
    assert unloaded == ["shared.png"]


def test_persistent_group_requires_force_to_unload(monkeypatch):
    from nexora.assets.manager import AssetManager

    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")
    manager.register_group("core", persistent=True)
    manager.load_group("core")

    assert manager.unload_group("core") is False
    assert manager.group_ref_count("core") == 1

    assert manager.unload_group("core", force=True) is True
    assert manager.group_ref_count("core") == 0


def test_group_loading_stages_add_commit_stage(monkeypatch):
    from nexora.assets.manager import AssetManager

    monkeypatch.setattr("nexora.assets.manager.TextSystem.initialize", lambda self: None)
    manager = AssetManager("assets")
    manager.register_group("beach", textures=["world/beach.png"])

    task = FakeTask()
    monkeypatch.setattr(manager, "texture", lambda path, force_reload=False: object())

    stages = manager.add_group_loading_stages(task, "beach")

    assert stages[-1].name == "assets_group_beach"
    assert manager.group_ref_count("beach") == 0

    # Drive texture stage: first update loads and keeps 100% visible,
    # second update marks it done, then commit activates the group.
    texture_stage = next(stage for stage in stages if stage.name == "assets_texture")
    assert texture_stage.update_callback(0.016) is False
    assert texture_stage.update_callback(0.016) is True

    stages[-1].callback()
    assert manager.group_ref_count("beach") == 1
