from __future__ import annotations

from nexora.scene.scene import Scene


class SceneManager:
    """Manages loaded scenes and the currently active scene."""

    def __init__(self) -> None:
        self._scenes: dict[str, Scene] = {}
        self._active_scene: Scene | None = None

    @property
    def active_scene(self) -> Scene | None:
        return self._active_scene

    def load(self, scene: Scene) -> None:
        if scene.name in self._scenes:
            raise ValueError(
                f"A scene named '{scene.name}' is already loaded."
            )

        self._scenes[scene.name] = scene

    def unload(self, name: str) -> None:
        scene = self._scenes.get(name)

        if scene is None:
            raise KeyError(
                f"Scene '{name}' is not loaded."
            )

        if scene is self._active_scene:
            self._active_scene = None

        scene.destroy()
        del self._scenes[name]

    def activate(self, name: str) -> Scene:
        scene = self._scenes.get(name)

        if scene is None:
            raise KeyError(
                f"Scene '{name}' is not loaded."
            )

        self._active_scene = scene

        return scene

    def get(self, name: str) -> Scene | None:
        return self._scenes.get(name)

    def is_loaded(self, name: str) -> bool:
        return name in self._scenes

    def clear(self) -> None:
        for scene in tuple(self._scenes.values()):
            scene.destroy()

        self._scenes.clear()
        self._active_scene = None