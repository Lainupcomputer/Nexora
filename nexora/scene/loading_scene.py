from __future__ import annotations

from collections.abc import Callable

from nexora.nodes import (
    Label,
    ProgressBar,
)

from nexora.scene.loading import (
    SceneLoadTask,
)

from nexora.scene.scene import (
    Scene,
    SceneState,
)


class LoadingScene(Scene):
    """
    Generic Nexora loading scene.

    Displays:

        - title
        - status text
        - progress bar
        - percentage
        - current loading stage

    The LoadingScene does not know what is being loaded.

    It only observes a SceneLoadTask.

    Example:

        task = SceneLoadTask(
            "Dungeon"
        )

        loading_scene.configure(
            task,
            target_name="Dungeon",
            on_completed=...,
        )
    """

    def __init__(
        self,
        name: str = "Loading",
    ) -> None:
        super().__init__(
            name
        )

        # ======================================================
        # Task state
        # ======================================================

        self._task: (
            SceneLoadTask | None
        ) = None

        self._target_name: (
            str | None
        ) = None

        self._on_completed: (
            Callable[[], None] | None
        ) = None

        self._on_failed: (
            Callable[
                [BaseException],
                None,
            ]
            | None
        ) = None

        self._completion_dispatched = False
        self._failure_dispatched = False

        # ======================================================
        # Title
        # ======================================================

        self.title_label = (
            self.ui.create_child(
                "LoadingTitle",
                node_type=Label,
            )
        )

        self.title_label.text = (
            "Loading..."
        )

        self.title_label.anchor = (
            0.5,
            0.5,
        )

        self.title_label.pivot = (
            0.5,
            0.5,
        )

        self.title_label.position = (
            0.0,
            -110.0,
        )

        self.title_label.scale = 1.45

        # ======================================================
        # Status
        # ======================================================

        self.status_label = (
            self.ui.create_child(
                "LoadingStatus",
                node_type=Label,
            )
        )

        self.status_label.text = (
            "Preparing..."
        )

        self.status_label.anchor = (
            0.5,
            0.5,
        )

        self.status_label.pivot = (
            0.5,
            0.5,
        )

        self.status_label.position = (
            0.0,
            -45.0,
        )

        self.status_label.scale = 0.9

        # ======================================================
        # Progress bar
        # ======================================================

        self.progress_bar = (
            self.ui.create_child(
                "LoadingProgress",
                node_type=ProgressBar,
            )
        )

        self.progress_bar.orientation = (
            "horizontal"
        )

        self.progress_bar.length = 520.0
        self.progress_bar.thickness = 28.0

        self.progress_bar.min_value = 0.0
        self.progress_bar.max_value = 100.0

        self.progress_bar.set_value(
            0.0
        )

        self.progress_bar.anchor = (
            0.5,
            0.5,
        )

        self.progress_bar.pivot = (
            0.5,
            0.5,
        )

        self.progress_bar.position = (
            0.0,
            10.0,
        )

        # ======================================================
        # Percentage
        # ======================================================

        self.percent_label = (
            self.ui.create_child(
                "LoadingPercent",
                node_type=Label,
            )
        )

        self.percent_label.text = (
            "0%"
        )

        self.percent_label.anchor = (
            0.5,
            0.5,
        )

        self.percent_label.pivot = (
            0.5,
            0.5,
        )

        self.percent_label.position = (
            0.0,
            60.0,
        )

        self.percent_label.scale = 0.9

        # ======================================================
        # Stage
        # ======================================================

        self.stage_label = (
            self.ui.create_child(
                "LoadingStage",
                node_type=Label,
            )
        )

        self.stage_label.text = (
            ""
        )

        self.stage_label.anchor = (
            0.5,
            0.5,
        )

        self.stage_label.pivot = (
            0.5,
            0.5,
        )

        self.stage_label.position = (
            0.0,
            100.0,
        )

        self.stage_label.scale = 0.75

        # ======================================================
        # Error
        # ======================================================

        self.error_label = (
            self.ui.create_child(
                "LoadingError",
                node_type=Label,
            )
        )

        self.error_label.text = ""

        self.error_label.anchor = (
            0.5,
            0.5,
        )

        self.error_label.pivot = (
            0.5,
            0.5,
        )

        self.error_label.position = (
            0.0,
            150.0,
        )

        self.error_label.scale = 0.75

    # ==========================================================
    # TASK
    # ==========================================================

    @property
    def task(
        self,
    ) -> SceneLoadTask | None:
        return self._task

    @property
    def target_name(
        self,
    ) -> str | None:
        return self._target_name

    @property
    def loading(
        self,
    ) -> bool:
        task = self._task

        if task is None:
            return False

        return (
            task.running
            or task.pending
        )

    # ==========================================================
    # CONFIGURE
    # ==========================================================

    def configure(
        self,
        task: SceneLoadTask,
        *,
        target_name: str,
        on_completed: (
            Callable[[], None]
            | None
        ) = None,
        on_failed: (
            Callable[
                [BaseException],
                None,
            ]
            | None
        ) = None,
    ) -> None:
        """
        Configure the LoadingScene for a new loading operation.
        """

        self._ensure_alive()

        if not isinstance(
            task,
            SceneLoadTask,
        ):
            raise TypeError(
                "task must be a SceneLoadTask."
            )

        if not target_name:
            raise ValueError(
                "target_name cannot be empty."
            )

        if self.loading:
            raise RuntimeError(
                "LoadingScene is already processing a task."
            )

        self._task = task

        self._target_name = str(
            target_name
        )

        self._on_completed = (
            on_completed
        )

        self._on_failed = (
            on_failed
        )

        self._completion_dispatched = False
        self._failure_dispatched = False

        self._reset_ui()

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def on_enter(
        self,
        previous_state: SceneState,
    ) -> None:
        self._sync_ui()

    def on_exit(
        self,
        previous_state: SceneState,
    ) -> None:
        pass

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if (
            self.state
            != SceneState.ACTIVE
        ):
            return

        task = self._task

        # ------------------------------------------------------
        # No task configured
        # ------------------------------------------------------

        if task is None:
            super().update(
                delta_time
            )

            return

        # ------------------------------------------------------
        # Advance loading
        # ------------------------------------------------------

        if (
            not task.done
            and not task.failed
            and not task.cancelled
        ):
            task.update(
                delta_time
            )

        # ------------------------------------------------------
        # Refresh UI
        # ------------------------------------------------------

        self._sync_ui()

        # ------------------------------------------------------
        # Failed
        # ------------------------------------------------------

        if task.failed:
            self._dispatch_failure()

            super().update(
                delta_time
            )

            return

        # ------------------------------------------------------
        # Cancelled
        # ------------------------------------------------------

        if task.cancelled:
            super().update(
                delta_time
            )

            return

        # ------------------------------------------------------
        # Completed
        #
        # Important:
        #
        # The completion callback may switch scenes.
        # Therefore do not continue updating this scene
        # afterwards.
        # ------------------------------------------------------

        if task.done:
            self._dispatch_completion()

            return

        # ------------------------------------------------------
        # Normal scene update
        # ------------------------------------------------------

        super().update(
            delta_time
        )

    # ==========================================================
    # UI
    # ==========================================================

    def _reset_ui(
        self,
    ) -> None:
        task = self._task

        if task is None:
            self.title_label.text = (
                "Loading..."
            )

        else:
            self.title_label.text = (
                f"Loading {task.name}"
            )

        self.status_label.text = (
            "Preparing..."
        )

        self.progress_bar.set_value(
            0.0
        )

        self.percent_label.text = (
            "0%"
        )

        self.stage_label.text = ""

        self.error_label.text = ""

    def _sync_ui(
        self,
    ) -> None:
        task = self._task

        if task is None:
            return

        info = (
            task.progress_info
        )

        progress = max(
            0.0,
            min(
                1.0,
                info.progress,
            ),
        )

        percent = int(
            round(
                progress
                * 100.0
            )
        )

        # ------------------------------------------------------
        # Title
        # ------------------------------------------------------

        self.title_label.text = (
            f"Loading {task.name}"
        )

        # ------------------------------------------------------
        # Status
        # ------------------------------------------------------

        self.status_label.text = (
            info.status
        )

        # ------------------------------------------------------
        # Progress
        # ------------------------------------------------------

        self.progress_bar.set_value(
            progress
            * 100.0
        )

        self.percent_label.text = (
            f"{percent}%"
        )

        # ------------------------------------------------------
        # Stage
        # ------------------------------------------------------

        if info.stage_count > 0:
            visible_stage = min(
                info.stage_index + 1,
                info.stage_count,
            )

            self.stage_label.text = (
                f"Stage "
                f"{visible_stage}"
                f" / "
                f"{info.stage_count}"
            )

        else:
            self.stage_label.text = ""

        # ------------------------------------------------------
        # Error
        # ------------------------------------------------------

        if task.failed:
            if task.error is None:
                self.error_label.text = (
                    "Loading failed."
                )

            else:
                self.error_label.text = (
                    f"Error: "
                    f"{task.error}"
                )

        else:
            self.error_label.text = ""

    # ==========================================================
    # COMPLETION
    # ==========================================================

    def _dispatch_completion(
        self,
    ) -> None:
        if self._completion_dispatched:
            return

        self._completion_dispatched = True

        callback = (
            self._on_completed
        )

        if callback is not None:
            callback()

    # ==========================================================
    # FAILURE
    # ==========================================================

    def _dispatch_failure(
        self,
    ) -> None:
        if self._failure_dispatched:
            return

        self._failure_dispatched = True

        callback = (
            self._on_failed
        )

        task = self._task

        if (
            callback is not None
            and task is not None
            and task.error is not None
        ):
            callback(
                task.error
            )

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear_task(
        self,
    ) -> None:
        """
        Remove the current task after loading has finished.
        """

        if self.loading:
            raise RuntimeError(
                "Cannot clear a running loading task."
            )

        self._task = None
        self._target_name = None

        self._on_completed = None
        self._on_failed = None

        self._completion_dispatched = False
        self._failure_dispatched = False

        self._reset_ui()

    # ==========================================================
    # DESTROY
    # ==========================================================

    def destroy(
        self,
    ) -> None:
        self._task = None

        self._on_completed = None
        self._on_failed = None

        super().destroy()