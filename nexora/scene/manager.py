from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nexora.scene.loading import (
    SceneLoadTask,
)

from nexora.scene.loading_scene import (
    LoadingScene,
)

from nexora.scene.scene import (
    Scene,
    SceneState,
)

from nexora.scene.transition import (
    SceneTransition,
)

from nexora.scene.serialization import (
    SceneSerializer,
)


SceneFactory = Callable[
    [],
    Scene,
]


@dataclass(slots=True)
class SceneRegistration:
    """
    Registered scene factory.

    A registered scene does not need to be loaded immediately.

    Parameters
    ----------
    name:
        Registered scene name.

    factory:
        Callable which creates a fresh Scene instance.

    keep_loaded:
        True:
            Keep the scene instance alive after leaving it.

        False:
            Destroy and unload the scene automatically after
            leaving it.
    """

    name: str
    factory: SceneFactory
    keep_loaded: bool = True


@dataclass(slots=True)
class SerializedSceneRegistration:
    """Registered .nxscene source."""

    name: str
    path: Path
    asset_groups: tuple[str, ...]
    metadata: dict[str, Any]
    keep_loaded: bool = False


class SceneManager:
    """
    Nexora scene manager.

    Supports:

        - manually loaded scenes
        - registered scene factories
        - lazy loading
        - automatic unloading
        - persistent / transient scenes
        - scene reloading
        - scene lifecycle
        - scene stack
        - pause / resume
        - scene transitions
        - loading scenes
        - SceneLoadTask integration

    Basic example
    -------------

        manager.register(
            "HQ",
            create_hq,
            keep_loaded=True,
        )

        manager.register(
            "Dungeon",
            create_dungeon,
            keep_loaded=False,
        )

        manager.change_scene(
            "HQ"
        )

    Loading example
    ---------------

        manager.begin_loading(
            "Dungeon",
            dungeon_task,
            loading_scene="Loading",
        )
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

    # ==========================================================
    # ACTIVE SCENE
    # ==========================================================

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

    # ==========================================================
    # LOADED SCENES
    # ==========================================================

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

    # ==========================================================
    # REGISTERED SCENES
    # ==========================================================

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

    # ==========================================================
    # STACK
    # ==========================================================

    @property
    def stack(
        self,
    ) -> tuple[
        Scene,
        ...
    ]:
        return tuple(
            self._scene_stack
        )

    @property
    def stack_names(
        self,
    ) -> tuple[
        str,
        ...
    ]:
        return tuple(
            scene.name
            for scene in self._scene_stack
        )

    @property
    def stack_depth(
        self,
    ) -> int:
        return len(
            self._scene_stack
        )

    # ==========================================================
    # TRANSITION
    # ==========================================================

    @property
    def transition(
        self,
    ) -> SceneTransition | None:
        """
        Return the currently active scene transition.

        Finished transitions are cleared automatically.
        """

        transition = (
            self._transition
        )

        if (
            transition is not None
            and transition.finished
        ):
            self._transition = None

            return None

        return transition

    @property
    def transitioning(
        self,
    ) -> bool:
        transition = (
            self.transition
        )

        return (
            transition is not None
            and transition.running
        )

    # ==========================================================
    # SERIALIZED SCENE SERVICES
    # ==========================================================

    @property
    def scene_serializer(self) -> SceneSerializer | None:
        return self._scene_serializer

    def bind_scene_serializer(
        self,
        serializer: SceneSerializer,
    ) -> None:
        if not isinstance(serializer, SceneSerializer):
            raise TypeError("serializer must be a SceneSerializer.")
        self._scene_serializer = serializer

    def bind_assets(self, asset_manager) -> None:
        if asset_manager is None:
            raise ValueError("asset_manager cannot be None.")
        self._asset_manager = asset_manager

    def bind_serialization_context_provider(
        self,
        provider: Callable[[], dict[str, Any]] | None,
    ) -> None:
        if provider is not None and not callable(provider):
            raise TypeError("provider must be callable or None.")
        self._serialization_context_provider = provider

    def _serialization_context(
        self,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if self._serialization_context_provider is not None:
            provided = self._serialization_context_provider()
            if provided:
                context.update(dict(provided))
        if extra:
            context.update(dict(extra))
        return context

    def _require_scene_serializer(self) -> SceneSerializer:
        if self._scene_serializer is None:
            raise RuntimeError(
                "SceneManager has no SceneSerializer. "
                "Bind one before using serialized scenes."
            )
        return self._scene_serializer

    def _require_asset_manager(self):
        if self._asset_manager is None:
            raise RuntimeError(
                "SceneManager has no AssetManager. "
                "Bind one before loading serialized scene asset groups."
            )
        return self._asset_manager

    # ==========================================================
    # REGISTRATION
    # ==========================================================

    def register(
        self,
        name: str,
        factory: SceneFactory,
        *,
        keep_loaded: bool = True,
    ) -> None:
        """
        Register a scene factory.

        Registration itself does not create the Scene.

        Example:

            scenes.register(
                "Dungeon",
                lambda: DungeonScene(),
                keep_loaded=False,
            )
        """

        name = str(
            name
        )

        if not name:
            raise ValueError(
                "Scene name cannot be empty."
            )

        if not callable(
            factory
        ):
            raise TypeError(
                "Scene factory must be callable."
            )

        if name in self._registrations:
            raise ValueError(
                f"Scene '{name}' is already registered."
            )

        self._registrations[
            name
        ] = SceneRegistration(
            name=name,
            factory=factory,
            keep_loaded=bool(
                keep_loaded
            ),
        )

    def unregister(
        self,
        name: str,
        *,
        unload: bool = False,
    ) -> None:
        """
        Remove a scene registration.

        unload=True also destroys an existing loaded instance.
        """

        self._ensure_not_transitioning()

        if name not in self._registrations:
            raise KeyError(
                f"Scene '{name}' is not registered."
            )

        if (
            unload
            and self.is_loaded(
                name
            )
        ):
            self.unload(
                name
            )

        del self._registrations[
            name
        ]

    def is_registered(
        self,
        name: str,
    ) -> bool:
        return (
            name in self._registrations
            or name in self._serialized_registrations
        )

    def registration(
        self,
        name: str,
    ) -> SceneRegistration | None:
        return self._registrations.get(
            name
        )

    # ==========================================================
    # SERIALIZED REGISTRATION
    # ==========================================================

    def register_serialized(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        keep_loaded: bool = False,
        replace: bool = False,
    ) -> SerializedSceneRegistration:
        serializer = self._require_scene_serializer()
        source = Path(path).expanduser().resolve()
        metadata = serializer.inspect_metadata(source)

        resolved_name = str(name or metadata["name"]).strip()
        if not resolved_name:
            raise ValueError("Serialized scene name cannot be empty.")

        if resolved_name in self._registrations:
            raise ValueError(
                f"Scene '{resolved_name}' already has a factory registration."
            )
        if resolved_name in self._scenes:
            raise ValueError(
                f"Scene '{resolved_name}' is already loaded."
            )
        if resolved_name in self._serialized_registrations and not replace:
            raise ValueError(
                f"Serialized scene '{resolved_name}' is already registered."
            )

        groups = tuple(
            dict.fromkeys(str(group).strip() for group in metadata.get("asset_groups", ()) if str(group).strip())
        )
        registration = SerializedSceneRegistration(
            name=resolved_name,
            path=source,
            asset_groups=groups,
            metadata=dict(metadata.get("metadata", {})),
            keep_loaded=bool(keep_loaded),
        )
        self._serialized_registrations[resolved_name] = registration
        return registration

    def unregister_serialized(
        self,
        name: str,
        *,
        unload: bool = False,
    ) -> None:
        self._ensure_not_transitioning()
        if name not in self._serialized_registrations:
            raise KeyError(f"Serialized scene '{name}' is not registered.")
        if unload and self.is_loaded(name):
            self.unload(name)
        del self._serialized_registrations[name]

    def serialized_registration(
        self,
        name: str,
    ) -> SerializedSceneRegistration | None:
        return self._serialized_registrations.get(name)

    @property
    def serialized_names(self) -> tuple[str, ...]:
        return tuple(self._serialized_registrations.keys())

    def resolve_serialized_scene_name(
        self,
        reference: str | Path,
    ) -> str:
        """Resolve a serialized scene name from a name or .nxscene path.

        Exact registered names win. Path references are matched against the
        registered SerializedSceneRegistration paths. A basename-only match is
        accepted when it is unique.
        """

        raw = str(reference).strip()
        if not raw:
            raise ValueError("Serialized scene reference cannot be empty.")

        if raw in self._serialized_registrations:
            return raw

        candidate_path = Path(raw).expanduser()
        try:
            resolved_path = candidate_path.resolve()
        except OSError:
            resolved_path = candidate_path

        exact_matches: list[str] = []
        basename_matches: list[str] = []

        for name, registration in self._serialized_registrations.items():
            registered_path = registration.path

            if registered_path == resolved_path:
                exact_matches.append(name)
                continue

            if registered_path.name == candidate_path.name:
                basename_matches.append(name)

        if len(exact_matches) == 1:
            return exact_matches[0]

        if len(exact_matches) > 1:
            raise ValueError(
                f"Serialized scene reference {raw!r} is ambiguous."
            )

        if len(basename_matches) == 1:
            return basename_matches[0]

        if len(basename_matches) > 1:
            raise ValueError(
                f"Serialized scene basename {candidate_path.name!r} is ambiguous."
            )

        raise KeyError(
            f"No registered serialized scene matches {raw!r}."
        )

    def load_serialized_registered(
        self,
        name: str,
        *,
        activate: bool = False,
        context: dict[str, Any] | None = None,
        force_reload_assets: bool = False,
    ) -> Scene:
        existing = self._scenes.get(name)
        if existing is not None:
            if activate:
                self.change_scene(name)
            return existing

        registration = self._serialized_registrations.get(name)
        if registration is None:
            raise KeyError(f"Serialized scene '{name}' is not registered.")

        assets = self._require_asset_manager() if registration.asset_groups else None
        acquired = False
        if assets is not None:
            assets.load_groups(
                registration.asset_groups,
                force_reload=force_reload_assets,
            )
            acquired = True

        try:
            scene = self._require_scene_serializer().load(
                registration.path,
                context=self._serialization_context(context),
            )
            if scene.name != name:
                raise ValueError(
                    f"Serialized scene registered as '{name}' loaded as '{scene.name}'."
                )
            self._scenes[name] = scene
            if acquired:
                self._managed_scene_groups[name] = registration.asset_groups
        except Exception:
            if acquired:
                assets.unload_groups(registration.asset_groups)
            raise

        if activate:
            self.change_scene(name)
        return scene

    # ==========================================================
    # LOAD EXISTING INSTANCE
    # ==========================================================

    def load(
        self,
        scene: Scene,
        *,
        activate: bool = False,
    ) -> Scene:
        """
        Load an already-created Scene instance.

        This is useful for scenes constructed manually instead
        of through a registered factory.
        """

        if not isinstance(
            scene,
            Scene,
        ):
            raise TypeError(
                "scene must be a Scene instance."
            )

        if scene.destroyed:
            raise ValueError(
                "Cannot load a destroyed scene."
            )

        if scene.name in self._scenes:
            raise ValueError(
                f"Scene '{scene.name}' "
                f"is already loaded."
            )

        self._scenes[
            scene.name
        ] = scene

        if activate:
            self.change_scene(
                scene.name
            )

        return scene

    # ==========================================================
    # LOAD REGISTERED SCENE
    # ==========================================================

    def load_registered(
        self,
        name: str,
        *,
        activate: bool = False,
    ) -> Scene:
        """
        Construct a registered scene and load it.

        If the scene is already loaded, the existing instance
        is returned.
        """

        existing = (
            self._scenes.get(
                name
            )
        )

        if existing is not None:
            if activate:
                self.change_scene(
                    name
                )

            return existing

        registration = (
            self._registrations.get(
                name
            )
        )

        if registration is None:
            raise KeyError(
                f"Scene '{name}' is not registered."
            )

        scene = (
            registration.factory()
        )

        if not isinstance(
            scene,
            Scene,
        ):
            raise TypeError(
                f"Factory for scene '{name}' "
                f"did not return a Scene."
            )

        if scene.destroyed:
            raise ValueError(
                f"Factory for scene '{name}' "
                f"returned a destroyed Scene."
            )

        if scene.name != name:
            raise ValueError(
                f"Scene factory registered as '{name}' "
                f"returned scene named '{scene.name}'."
            )

        self._scenes[
            name
        ] = scene

        if activate:
            self.change_scene(
                name
            )

        return scene

    # ==========================================================
    # ENSURE LOADED
    # ==========================================================

    def ensure_loaded(
        self,
        name: str,
    ) -> Scene:
        """
        Return the loaded scene.

        If it is registered but not yet loaded, construct it
        through the registered factory.
        """

        scene = (
            self._scenes.get(
                name
            )
        )

        if scene is not None:
            return scene

        if name in self._serialized_registrations:
            return self.load_serialized_registered(name)

        return self.load_registered(
            name
        )

    # ==========================================================
    # RELOAD
    # ==========================================================

    def reload(
        self,
        name: str,
        *,
        activate: bool = False,
    ) -> Scene:
        """
        Destroy and recreate a registered Scene.

        If the Scene was active before reloading, the newly
        created instance becomes active again automatically.
        """

        self._ensure_not_transitioning()

        if name not in self._registrations:
            raise KeyError(
                f"Scene '{name}' is not registered."
            )

        if self.is_on_stack(
            name
        ):
            raise RuntimeError(
                "Cannot reload a scene while it is "
                "on the scene stack."
            )

        was_active = (
            self.active_scene_name
            == name
        )

        if self.is_loaded(
            name
        ):
            self.unload(
                name
            )

        scene = (
            self.load_registered(
                name
            )
        )

        if (
            activate
            or was_active
        ):
            self.change_scene(
                name
            )

        return scene

    # ==========================================================
    # UNLOAD
    # ==========================================================

    def unload(
        self,
        name: str,
    ) -> None:
        """
        Destroy and remove a loaded Scene.

        Its registration remains available.
        """

        self._ensure_not_transitioning()

        scene = (
            self._get_loaded_required(
                name
            )
        )

        if scene in self._scene_stack:
            raise RuntimeError(
                "Cannot unload a scene while it is "
                "on the scene stack."
            )

        if (
            scene
            is self._active_scene
        ):
            scene.exit()

            self._active_scene = None

        scene.destroy()

        del self._scenes[
            name
        ]

        self._release_managed_scene_groups(name)

    # ==========================================================
    # CHANGE SCENE
    # ==========================================================

    def activate(
        self,
        name: str,
    ) -> Scene:
        """
        Alias for change_scene().
        """

        return self.change_scene(
            name
        )

    def change_scene(
        self,
        name: str,
        *,
        unload_previous: bool | None = None,
        transition: (
            SceneTransition | None
        ) = None,
    ) -> Scene:
        """
        Change the active Scene.

        Registered scenes are lazy-loaded automatically.

        unload_previous
        ----------------

        True
            Always destroy the previous Scene.

        False
            Always keep the previous Scene loaded.

        None
            Use the previous Scene's registration policy.

            keep_loaded=True
                preserve it

            keep_loaded=False
                destroy it
        """

        self._ensure_not_transitioning()

        next_scene = (
            self.ensure_loaded(
                name
            )
        )

        current_scene = (
            self._active_scene
        )

        # ------------------------------------------------------
        # Already active
        # ------------------------------------------------------

        if (
            current_scene
            is next_scene
            and not self._scene_stack
        ):
            if (
                next_scene.state
                == SceneState.PAUSED
            ):
                next_scene.resume()

            return next_scene

        # ------------------------------------------------------
        # Resolve unload policy
        # ------------------------------------------------------

        resolved_unload = (
            self._resolve_unload_previous(
                current_scene,
                unload_previous,
            )
        )

        # ------------------------------------------------------
        # Immediate switch
        # ------------------------------------------------------

        if transition is None:
            return (
                self._change_scene_immediate(
                    name,
                    unload_previous=(
                        resolved_unload
                    ),
                )
            )

        # ------------------------------------------------------
        # Transition
        # ------------------------------------------------------

        self._transition = (
            transition
        )

        try:
            transition.start(
                self,
                next_scene,
                unload_previous=(
                    resolved_unload
                ),
            )

        except Exception:
            self._transition = None
            raise

        return next_scene

    # ==========================================================
    # UNLOAD POLICY
    # ==========================================================

    def _resolve_unload_previous(
        self,
        scene: Scene | None,
        requested: bool | None,
    ) -> bool:
        """
        Resolve whether the previous Scene should be destroyed.
        """

        if requested is not None:
            return bool(
                requested
            )

        if scene is None:
            return False

        registration = (
            self._registrations.get(
                scene.name
            )
        )

        if registration is not None:
            return not registration.keep_loaded

        serialized = self._serialized_registrations.get(scene.name)
        if serialized is not None:
            return not serialized.keep_loaded

        # ------------------------------------------------------
        # Manually loaded scenes are persistent by default.
        # ------------------------------------------------------

        return False

    # ==========================================================
    # IMMEDIATE CHANGE
    # ==========================================================

    def _change_scene_immediate(
        self,
        name: str,
        *,
        unload_previous: bool = False,
    ) -> Scene:
        """
        Internal immediate Scene switch.

        Used by both direct switches and SceneTransition.
        """

        next_scene = (
            self.ensure_loaded(
                name
            )
        )

        current_scene = (
            self._active_scene
        )

        # ------------------------------------------------------
        # Already active
        # ------------------------------------------------------

        if (
            current_scene
            is next_scene
            and not self._scene_stack
        ):
            if (
                next_scene.state
                == SceneState.PAUSED
            ):
                next_scene.resume()

            return next_scene

        # ------------------------------------------------------
        # Remove overlays
        # ------------------------------------------------------

        self._clear_stack_internal()

        current_scene = (
            self._active_scene
        )

        # ------------------------------------------------------
        # Exit current scene
        # ------------------------------------------------------

        if current_scene is not None:
            current_scene.exit()

        # ------------------------------------------------------
        # Activate next scene
        # ------------------------------------------------------

        self._active_scene = (
            next_scene
        )

        try:
            next_scene.enter()

        except Exception:
            # --------------------------------------------------
            # Restore previous scene if activation fails.
            # --------------------------------------------------

            self._active_scene = (
                current_scene
            )

            if (
                current_scene is not None
                and not current_scene.destroyed
            ):
                try:
                    current_scene.enter()

                except Exception:
                    self._active_scene = None

            raise

        # ------------------------------------------------------
        # Destroy previous scene only after the new one entered
        # successfully.
        # ------------------------------------------------------

        if (
            unload_previous
            and current_scene is not None
            and current_scene is not next_scene
        ):
            previous_name = (
                current_scene.name
            )

            current_scene.destroy()

            self._scenes.pop(
                previous_name,
                None,
            )

            self._release_managed_scene_groups(previous_name)

        return next_scene

    # ==========================================================
    # LOADING
    # ==========================================================

    def begin_loading(
        self,
        target_name: str,
        task: SceneLoadTask,
        *,
        loading_scene: str = "Loading",
        enter_transition: (
            SceneTransition | None
        ) = None,
        exit_transition: (
            SceneTransition | None
        ) = None,
        unload_previous: (
            bool | None
        ) = None,
    ) -> LoadingScene:
        """
        Start a SceneLoadTask through a LoadingScene.

        Flow:

            current scene

                ↓

            loading scene

                ↓

            SceneLoadTask runs incrementally

                ↓

            target scene

        The target Scene is intentionally NOT constructed before
        the task finishes.

        This allows procedural generation tasks to prepare data
        first and the target Scene factory to consume that data.

        Parameters
        ----------
        target_name:
            Name of the Scene to activate after loading.

        task:
            SceneLoadTask containing the loading/generation work.

        loading_scene:
            Name of a loaded or registered LoadingScene.

        enter_transition:
            Optional transition into the LoadingScene.

        exit_transition:
            Optional transition from LoadingScene into target.

        unload_previous:
            Override unloading behavior for the Scene that was
            active before entering the loading screen.
        """

        self._ensure_not_transitioning()

        if not isinstance(
            task,
            SceneLoadTask,
        ):
            raise TypeError(
                "task must be a SceneLoadTask."
            )

        target_name = str(
            target_name
        )

        if not target_name:
            raise ValueError(
                "target_name cannot be empty."
            )

        # ------------------------------------------------------
        # Target must be known, but must NOT be constructed yet.
        # ------------------------------------------------------

        if (
            target_name not in self._scenes
            and target_name not in self._registrations
            and target_name not in self._serialized_registrations
        ):
            raise KeyError(
                f"Scene '{target_name}' is neither "
                f"loaded nor registered."
            )

        # ------------------------------------------------------
        # Resolve loading scene
        # ------------------------------------------------------

        scene = (
            self.ensure_loaded(
                loading_scene
            )
        )

        if not isinstance(
            scene,
            LoadingScene,
        ):
            raise TypeError(
                f"Scene '{loading_scene}' must be "
                f"a LoadingScene."
            )

        # ------------------------------------------------------
        # Completion callback
        # ------------------------------------------------------

        def loading_completed() -> None:
            self.change_scene(
                target_name,
                transition=(
                    exit_transition
                ),
            )

        # ------------------------------------------------------
        # Failure callback
        #
        # Default behaviour is intentionally conservative:
        #
        # stay on the LoadingScene and display the error.
        # ------------------------------------------------------

        def loading_failed(
            error: BaseException,
        ) -> None:
            print(
                f"[SceneManager] Loading "
                f"'{target_name}' failed: "
                f"{error}"
            )

        # ------------------------------------------------------
        # Configure loading scene
        # ------------------------------------------------------

        scene.configure(
            task,
            target_name=target_name,
            on_completed=(
                loading_completed
            ),
            on_failed=(
                loading_failed
            ),
        )

        # ------------------------------------------------------
        # Enter loading screen
        # ------------------------------------------------------

        self.change_scene(
            loading_scene,
            unload_previous=(
                unload_previous
            ),
            transition=(
                enter_transition
            ),
        )

        return scene

    # ==========================================================
    # SERIALIZED LOADING + ASSET LIFECYCLE
    # ==========================================================

    def _release_managed_scene_groups(
        self,
        scene_name: str,
    ) -> None:
        groups = self._managed_scene_groups.pop(scene_name, ())
        if not groups:
            return
        assets = self._require_asset_manager()
        assets.unload_groups(groups)

    def begin_serialized_loading(
        self,
        name: str,
        *,
        loading_scene: str = "Loading",
        enter_transition: SceneTransition | None = None,
        exit_transition: SceneTransition | None = None,
        unload_previous: bool | None = None,
        context: dict[str, Any] | None = None,
        force_reload_assets: bool = False,
    ) -> Scene:
        """Load a registered .nxscene through the existing LoadingScene.

        Order:
            metadata already registered
            -> acquire all scene asset groups
            -> Font -> Audio -> Texture
            -> deserialize scene + prefabs
            -> release transient previous scene
            -> activate target using the existing exit transition
        """
        self._ensure_not_transitioning()

        registration = self._serialized_registrations.get(name)
        if registration is None:
            raise KeyError(f"Serialized scene '{name}' is not registered.")

        if name in self._scenes:
            return self.change_scene(
                name,
                unload_previous=unload_previous,
                transition=exit_transition,
            )

        previous_scene = self._active_scene
        previous_name = None if previous_scene is None else previous_scene.name
        release_previous = self._resolve_unload_previous(
            previous_scene,
            unload_previous,
        )

        task = SceneLoadTask(f"Scene: {name}")
        assets = self._require_asset_manager() if registration.asset_groups else None

        if assets is not None:
            assets.add_groups_loading_stages(
                task,
                registration.asset_groups,
                force_reload=force_reload_assets,
            )

        acquired_groups = bool(registration.asset_groups)

        def deserialize() -> None:
            try:
                scene = self._require_scene_serializer().load(
                    registration.path,
                    context=self._serialization_context(context),
                )
                if scene.name != name:
                    raise ValueError(
                        f"Serialized scene registered as '{name}' loaded as '{scene.name}'."
                    )
                if name in self._scenes:
                    raise ValueError(f"Scene '{name}' became loaded during serialized loading.")
                self._scenes[name] = scene
                if acquired_groups:
                    self._managed_scene_groups[name] = registration.asset_groups
            except Exception:
                if acquired_groups and assets is not None:
                    assets.unload_groups(registration.asset_groups)
                raise

        task.add_stage(
            "deserialize_scene",
            status=f"Initialisiere Szene: {name}",
            callback=deserialize,
        )

        if release_previous and previous_name is not None:
            def release_previous_scene() -> None:
                if previous_name in self._scenes:
                    self.unload(previous_name)

            task.add_stage(
                "release_previous_scene",
                weight=0.05,
                status="Bereinige vorherige Szene...",
                callback=release_previous_scene,
            )

        # Preserve the previous scene while assets are loading. If its policy
        # is transient it is released by the final task stage above.
        return self.begin_loading(
            name,
            task,
            loading_scene=loading_scene,
            enter_transition=enter_transition,
            exit_transition=exit_transition,
            unload_previous=False,
        )

    # ==========================================================
    # PUSH SCENE
    # ==========================================================

    def push_scene(
        self,
        name: str,
    ) -> Scene:
        """
        Push a Scene above the current Scene.

        The previous Scene is paused and placed on the stack.

        Registered scenes are loaded automatically.
        """

        self._ensure_not_transitioning()

        next_scene = (
            self.ensure_loaded(
                name
            )
        )

        current_scene = (
            self._active_scene
        )

        if (
            current_scene
            is next_scene
        ):
            raise RuntimeError(
                "Cannot push the currently active scene."
            )

        if (
            next_scene
            in self._scene_stack
        ):
            raise RuntimeError(
                f"Scene '{name}' is already "
                f"on the stack."
            )

        # ------------------------------------------------------
        # Pause current scene
        # ------------------------------------------------------

        if current_scene is not None:
            if (
                current_scene.state
                == SceneState.ACTIVE
            ):
                current_scene.pause()

            self._scene_stack.append(
                current_scene
            )

        # ------------------------------------------------------
        # Activate pushed scene
        # ------------------------------------------------------

        self._active_scene = (
            next_scene
        )

        try:
            next_scene.enter()

        except Exception:
            # --------------------------------------------------
            # Restore old state
            # --------------------------------------------------

            self._active_scene = (
                current_scene
            )

            if current_scene is not None:
                if (
                    self._scene_stack
                    and self._scene_stack[-1]
                    is current_scene
                ):
                    self._scene_stack.pop()

                if (
                    current_scene.state
                    == SceneState.PAUSED
                ):
                    current_scene.resume()

            raise

        return next_scene

    # ==========================================================
    # POP SCENE
    # ==========================================================

    def pop_scene(
        self,
    ) -> Scene | None:
        """
        Pop the current Scene and resume the previous Scene.

        The popped Scene remains loaded.
        """

        self._ensure_not_transitioning()

        return (
            self._pop_scene_internal()
        )

    def _pop_scene_internal(
        self,
    ) -> Scene | None:
        current_scene = (
            self._active_scene
        )

        if not self._scene_stack:
            return None

        # ------------------------------------------------------
        # Exit overlay/current scene
        # ------------------------------------------------------

        if current_scene is not None:
            current_scene.exit()

        # ------------------------------------------------------
        # Restore previous scene
        # ------------------------------------------------------

        previous_scene = (
            self._scene_stack.pop()
        )

        self._active_scene = (
            previous_scene
        )

        if (
            previous_scene.state
            == SceneState.PAUSED
        ):
            previous_scene.resume()

        elif (
            previous_scene.state
            != SceneState.ACTIVE
        ):
            previous_scene.enter()

        return current_scene

    # ==========================================================
    # POP AND UNLOAD
    # ==========================================================

    def pop_scene_and_unload(
        self,
    ) -> Scene | None:
        """
        Pop the current Scene and destroy it.
        """

        self._ensure_not_transitioning()

        popped = (
            self._pop_scene_internal()
        )

        if popped is None:
            return None

        name = (
            popped.name
        )

        popped.destroy()

        self._scenes.pop(
            name,
            None,
        )

        return popped

    # ==========================================================
    # CLEAR STACK
    # ==========================================================

    def clear_stack(
        self,
    ) -> None:
        """
        Remove all stacked overlay scenes.
        """

        self._ensure_not_transitioning()

        self._clear_stack_internal()

    def _clear_stack_internal(
        self,
    ) -> None:
        while self._scene_stack:
            self._pop_scene_internal()

    # ==========================================================
    # DEACTIVATE
    # ==========================================================

    def deactivate(
        self,
    ) -> Scene | None:
        """
        Deactivate the current Scene without destroying it.
        """

        self._ensure_not_transitioning()

        self._clear_stack_internal()

        current_scene = (
            self._active_scene
        )

        if current_scene is None:
            return None

        if (
            current_scene.state
            in (
                SceneState.ACTIVE,
                SceneState.PAUSED,
            )
        ):
            current_scene.exit()

        self._active_scene = None

        return current_scene

    # ==========================================================
    # PAUSE
    # ==========================================================

    def pause(
        self,
    ) -> None:
        """
        Pause the currently active Scene.
        """

        self._ensure_not_transitioning()

        if self._active_scene is None:
            return

        self._active_scene.pause()

    # ==========================================================
    # RESUME
    # ==========================================================

    def resume(
        self,
    ) -> None:
        """
        Resume the currently paused Scene.
        """

        self._ensure_not_transitioning()

        if self._active_scene is None:
            return

        self._active_scene.resume()

    # ==========================================================
    # ACCESS
    # ==========================================================

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

    # ==========================================================
    # QUERY
    # ==========================================================

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

    def is_on_stack(
        self,
        name: str,
    ) -> bool:
        scene = (
            self._scenes.get(
                name
            )
        )

        if scene is None:
            return False

        return (
            scene
            in self._scene_stack
        )

    # ==========================================================
    # TRANSITION GUARD
    # ==========================================================

    def _ensure_not_transitioning(
        self,
    ) -> None:
        if self.transitioning:
            raise RuntimeError(
                "Cannot modify scenes while "
                "a scene transition is running."
            )

    # ==========================================================
    # CLEAR
    # ==========================================================

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
        # Transition
        # ------------------------------------------------------

        self._transition = None

        # ------------------------------------------------------
        # Optional registration cleanup
        # ------------------------------------------------------

        if clear_registrations:
            self._registrations.clear()