from __future__ import annotations

from typing import Any

from nexora.scene.loading import SceneLoadTask
from nexora.scene.loading_scene import LoadingScene
from nexora.scene.scene import Scene
from nexora.scene.transition import SceneTransition


class SceneLoadingMixin:
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
