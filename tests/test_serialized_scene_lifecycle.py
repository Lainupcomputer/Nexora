from pathlib import Path

from nexora.scene import LoadingScene, Scene, SceneLoadTask, SceneManager


class FakeSerializer:
    def __init__(self):
        self.loaded = []

    def inspect_metadata(self, path):
        return {
            "name": "HQ",
            "schema_version": 1,
            "asset_groups": ["core", "hq"],
            "metadata": {"kind": "world"},
        }

    def load(self, path, *, context=None):
        self.loaded.append((Path(path), dict(context or {})))
        scene = Scene("HQ")
        scene.asset_groups = ["core", "hq"]
        return scene


class FakeAssets:
    def __init__(self):
        self.calls = []
        self.refs = {"core": 0, "hq": 0}

    def load_groups(self, names, *, force_reload=False, callbacks=None):
        names = tuple(names)
        self.calls.append(("load_groups", names))
        for name in names:
            self.refs[name] = self.refs.get(name, 0) + 1
        return names

    def add_groups_loading_stages(self, task, names, **kwargs):
        names = tuple(names)
        self.calls.append(("add_groups_loading_stages", names))

        def commit():
            for name in names:
                self.refs[name] = self.refs.get(name, 0) + 1

        return [
            task.add_stage(
                "fake_assets",
                status="Initialisiere Assets: Font 100%",
                callback=commit,
            )
        ]

    def unload_groups(self, names, **kwargs):
        names = tuple(names)
        self.calls.append(("unload_groups", names))
        for name in names:
            self.refs[name] = max(0, self.refs.get(name, 0) - 1)
        return len(names)


def make_manager(tmp_path):
    serializer = FakeSerializer()
    assets = FakeAssets()
    manager = SceneManager()
    # Fake serializer deliberately duck-types the public serializer contract.
    manager._scene_serializer = serializer
    manager.bind_assets(assets)
    scene_file = tmp_path / "hq.nxscene"
    scene_file.write_bytes(b"fake")
    manager.register_serialized(scene_file, keep_loaded=False)
    return manager, serializer, assets


def test_direct_serialized_load_acquires_groups(tmp_path):
    manager, serializer, assets = make_manager(tmp_path)

    scene = manager.load_serialized_registered("HQ")

    assert scene.name == "HQ"
    assert manager.active_scene is None
    assert manager.scene_names == ("HQ",)
    assert assets.refs == {"core": 1, "hq": 1}
    assert manager.serialized_registration("HQ").asset_groups == ("core", "hq")
    assert len(serializer.loaded) == 1


def test_unload_serialized_scene_releases_owned_groups(tmp_path):
    manager, _serializer, assets = make_manager(tmp_path)
    manager.load_serialized_registered("HQ")

    manager.unload("HQ")

    assert assets.refs == {"core": 0, "hq": 0}
    assert "HQ" not in manager.scene_names


def test_begin_serialized_loading_uses_existing_loading_scene(tmp_path):
    manager, serializer, assets = make_manager(tmp_path)

    loading = LoadingScene("Loading")
    manager.load(loading)

    start = Scene("Start")
    manager.load(start, activate=True)

    manager.begin_serialized_loading(
        "HQ",
        loading_scene="Loading",
        context={"custom": 123},
    )

    assert manager.active_scene is loading
    assert ("add_groups_loading_stages", ("core", "hq")) in assets.calls

    # Drive the LoadingScene task through its public task object.
    task = loading.task
    assert isinstance(task, SceneLoadTask)

    for _ in range(20):
        if task.done:
            break

        task.update(0.016)

    assert task.done
    assert "HQ" in manager.scene_names
    assert serializer.loaded[0][1]["custom"] == 123
