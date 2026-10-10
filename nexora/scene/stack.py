from __future__ import annotations

from nexora.scene.scene import Scene, SceneState


class SceneStackMixin:
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
