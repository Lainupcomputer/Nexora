from __future__ import annotations

from typing import Any, Callable

from nexora.scene.scene import Scene
from nexora.scene.serialization import SceneSerializer
from nexora.scene.transition import SceneTransition
from nexora.scene.registry import (
    SceneRegistration,
    SerializedSceneRegistration,
    SceneRegistryMixin,
)
from nexora.scene.loader import SceneLoadingMixin
from nexora.scene.switching import SceneSwitchingMixin
from nexora.scene.stack import SceneStackMixin


class SceneManager(
    SceneRegistryMixin,
    SceneLoadingMixin,
    SceneSwitchingMixin,
    SceneStackMixin,
):
    """Nexora scene manager facade.

    Registration, loading, switching and stack behavior are implemented by
    focused internal mixins while this class owns the shared runtime state and
    stable public API.
    """
    def __init__(
        self,
        *,
        serializer: SceneSerializer | None = None,
    ) -> None:
        # ======================================================
        # Loaded scene instances
        # ======================================================

        self._scenes: dict[
            str,
            Scene,
        ] = {}

        # ======================================================
        # Registered scene factories
        # ======================================================

        self._registrations: dict[
            str,
            SceneRegistration,
        ] = {}

        # ======================================================
        # Serialized scene registrations
        # ======================================================

        self._serialized_registrations: dict[
            str,
            SerializedSceneRegistration,
        ] = {}

        self._scene_serializer = serializer
        self._asset_manager = None
        self._serialization_context_provider: (
            Callable[[], dict[str, Any]] | None
        ) = None

        # Scene name -> root asset groups acquired by this manager.
        self._managed_scene_groups: dict[
            str,
            tuple[str, ...],
        ] = {}

        # ======================================================
        # Active scene
        # ======================================================

        self._active_scene: (
            Scene | None
        ) = None

        # ======================================================
        # Scene stack
        # ======================================================

        self._scene_stack: list[
            Scene
        ] = []

        # ======================================================
        # Transition
        # ======================================================

        self._transition: (
            SceneTransition | None
        ) = None

    @property
    def active_scene(
        self,
    ) -> Scene | None:
        return self._active_scene

    @property
    def active_scene_name(
        self,
    ) -> str | None:
        if self._active_scene is None:
            return None

        return self._active_scene.name

    @property
    def scenes(
        self,
    ) -> tuple[
        Scene,
        ...
    ]:
        """
        Return all currently loaded scene instances.
        """

        return tuple(
            self._scenes.values()
        )

    @property
    def scene_names(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        """
        Return names of currently loaded scenes.
        """

        return tuple(
            self._scenes.keys()
        )

    @property
    def registered_names(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        """
        Return all registered scene names.
        """

        return tuple(
            dict.fromkeys(
                (*self._registrations.keys(), *self._serialized_registrations.keys())
            )
        )

    def get(
        self,
        name: str,
    ) -> Scene | None:
        """
        Return a loaded Scene.

        Registered-but-unloaded scenes return None.
        """

        return self._scenes.get(
            name
        )

    def _get_loaded_required(
        self,
        name: str,
    ) -> Scene:
        scene = (
            self._scenes.get(
                name
            )
        )

        if scene is None:
            raise KeyError(
                f"Scene '{name}' is not loaded."
            )

        return scene

    def is_loaded(
        self,
        name: str,
    ) -> bool:
        return (
            name
            in self._scenes
        )

    def is_active(
        self,
        name: str,
    ) -> bool:
        scene = (
            self._scenes.get(
                name
            )
        )

        return (
            scene is not None
            and scene
            is self._active_scene
        )

    def clear(
        self,
        *,
        clear_registrations: bool = False,
    ) -> None:
        """
        Destroy every currently loaded Scene.

        Registrations remain by default.

        Use:

            clear(
                clear_registrations=True
            )

        during complete engine shutdown if registrations should
        also be removed.
        """

        if self.transitioning:
            raise RuntimeError(
                "Cannot clear scenes while "
                "a scene transition is running."
            )

        # ------------------------------------------------------
        # Runtime state
        # ------------------------------------------------------

        self._scene_stack.clear()

        self._active_scene = None

        # ------------------------------------------------------
        # Destroy loaded scenes
        # ------------------------------------------------------

        for scene in tuple(
            self._scenes.values()
        ):
            scene.destroy()

        self._scenes.clear()

        # ------------------------------------------------------
        # Release manager-owned asset groups
        # ------------------------------------------------------

        for scene_name in tuple(
            self._managed_scene_groups.keys()
        ):
            self._release_managed_scene_groups(
                scene_name
            )

        self._managed_scene_groups.clear()

        # ------------------------------------------------------
        # Transition
        # ------------------------------------------------------

        self._transition = None

        # ------------------------------------------------------
        # Optional registration cleanup
        # ------------------------------------------------------

        if clear_registrations:
            self._registrations.clear()
            self._serialized_registrations.clear()
