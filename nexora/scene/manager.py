from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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
            self._registrations.keys()
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
            name
            in self._registrations
        )

    def registration(
        self,
        name: str,
    ) -> SceneRegistration | None:
        return self._registrations.get(
            name
        )

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

        # ------------------------------------------------------
        # Manually loaded scenes are persistent by default.
        # ------------------------------------------------------

        if registration is None:
            return False

        return not (
            registration.keep_loaded
        )

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