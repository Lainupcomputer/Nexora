from __future__ import annotations

from nexora.scene.scene import Scene, SceneState
from nexora.scene.transition import SceneTransition


class SceneSwitchingMixin:
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

    def _ensure_not_transitioning(
        self,
    ) -> None:
        if self.transitioning:
            raise RuntimeError(
                "Cannot modify scenes while "
                "a scene transition is running."
            )
