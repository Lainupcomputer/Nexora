from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class LoadingState(str, Enum):
    """
    Current state of a scene loading task.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class LoadingProgress:
    """
    Snapshot of the current loading progress.

    progress
        Normalized value between 0.0 and 1.0.

    status
        Human-readable status text.

    stage_name
        Name of the currently active loading stage.

    stage_index
        Zero-based stage index.

    stage_count
        Total number of stages.
    """

    progress: float = 0.0
    status: str = ""
    stage_name: str = ""
    stage_index: int = 0
    stage_count: int = 0
    stage_progress: float = 0.0


class LoadingStage:
    """
    One stage of a SceneLoadTask.

    A stage may either complete immediately or incrementally.

    callback
        Called once when the stage starts.

    update
        Called every frame while the stage is active.

        Return True when the stage is finished.

        Return False when more work remains.
    """

    def __init__(
        self,
        name: str,
        *,
        weight: float = 1.0,
        status: str | None = None,
        callback: Callable[[], None] | None = None,
        update: Callable[[float], bool] | None = None,
    ) -> None:
        if not name:
            raise ValueError(
                "Loading stage name cannot be empty."
            )

        if weight <= 0.0:
            raise ValueError(
                "Loading stage weight must be greater than zero."
            )

        if (
            callback is None
            and update is None
        ):
            raise ValueError(
                "LoadingStage requires callback or update."
            )

        self.name = str(
            name
        )

        self.status = (
            str(status)
            if status is not None
            else self.name
        )

        self.weight = float(
            weight
        )

        self.callback = (
            callback
        )

        self.update_callback = (
            update
        )

        self.started = False
        self.finished = False
        self._progress = 0.0


    @property
    def progress(
        self,
    ) -> float:
        return self._progress

    @progress.setter
    def progress(
        self,
        value: float,
    ) -> None:
        self._progress = max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    # ==========================================================
    # START
    # ==========================================================

    def start(
        self,
    ) -> None:
        if self.started:
            return

        self.started = True

        if self.callback is not None:
            self.callback()

            # --------------------------------------------------
            # Callback-only stages are complete immediately.
            # --------------------------------------------------

            if self.update_callback is None:
                self.finished = True
                self.progress = 1.0

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> bool:
        """
        Update the stage.

        Returns True when the stage is finished.
        """

        if self.finished:
            self.progress = 1.0
            return True

        if not self.started:
            self.start()

        if self.finished:
            self.progress = 1.0
            return True

        if self.update_callback is None:
            self.finished = True
            self.progress = 1.0
            return True

        result = self.update_callback(
            float(
                delta_time
            )
        )

        if result:
            self.finished = True
            self.progress = 1.0

        return self.finished


class SceneLoadTask:
    """
    Incremental scene loading task.

    Loading is split into weighted stages.

    Each call to update() advances the currently active stage.

    This lets the game continue rendering a LoadingScene while
    expensive preparation happens over multiple frames.

    Example
    -------

        task = SceneLoadTask(
            "Dungeon"
        )

        task.add_stage(
            "layout",
            status="Generating layout...",
            callback=generate_layout,
        )

        task.add_stage(
            "rooms",
            status="Building rooms...",
            callback=build_rooms,
        )

        task.add_stage(
            "navigation",
            status="Preparing navigation...",
            update=update_navigation,
        )
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        if not name:
            raise ValueError(
                "SceneLoadTask name cannot be empty."
            )

        self.name = str(
            name
        )

        self._stages: list[
            LoadingStage
        ] = []

        self._state = (
            LoadingState.PENDING
        )

        self._stage_index = 0

        self._error: (
            BaseException | None
        ) = None

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def state(
        self,
    ) -> LoadingState:
        return self._state

    @property
    def pending(
        self,
    ) -> bool:
        return (
            self._state
            == LoadingState.PENDING
        )

    @property
    def running(
        self,
    ) -> bool:
        return (
            self._state
            == LoadingState.RUNNING
        )

    @property
    def done(
        self,
    ) -> bool:
        return (
            self._state
            == LoadingState.COMPLETED
        )

    @property
    def failed(
        self,
    ) -> bool:
        return (
            self._state
            == LoadingState.FAILED
        )

    @property
    def cancelled(
        self,
    ) -> bool:
        return (
            self._state
            == LoadingState.CANCELLED
        )

    @property
    def error(
        self,
    ) -> BaseException | None:
        return self._error

    @property
    def stages(
        self,
    ) -> tuple[
        LoadingStage,
        ...
    ]:
        return tuple(
            self._stages
        )

    @property
    def stage_index(
        self,
    ) -> int:
        return self._stage_index

    @property
    def current_stage(
        self,
    ) -> LoadingStage | None:
        if not self._stages:
            return None

        if (
            self._stage_index
            >= len(
                self._stages
            )
        ):
            return None

        return self._stages[
            self._stage_index
        ]

    # ==========================================================
    # STAGES
    # ==========================================================

    def add_stage(
        self,
        name: str,
        *,
        weight: float = 1.0,
        status: str | None = None,
        callback: Callable[[], None] | None = None,
        update: Callable[[float], bool] | None = None,
    ) -> LoadingStage:
        """
        Add a loading stage.

        Stages can only be added before the task starts.
        """

        if (
            self._state
            != LoadingState.PENDING
        ):
            raise RuntimeError(
                "Cannot add stages after loading has started."
            )

        stage = LoadingStage(
            name,
            weight=weight,
            status=status,
            callback=callback,
            update=update,
        )

        self._stages.append(
            stage
        )

        return stage

    # ==========================================================
    # START
    # ==========================================================

    def start(
        self,
    ) -> None:
        if (
            self._state
            != LoadingState.PENDING
        ):
            return

        if not self._stages:
            self._state = (
                LoadingState.COMPLETED
            )

            return

        self._state = (
            LoadingState.RUNNING
        )

        self._stage_index = 0

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Advance the loading task by one frame.
        """

        if (
            self._state
            == LoadingState.PENDING
        ):
            self.start()

        if (
            self._state
            != LoadingState.RUNNING
        ):
            return

        stage = (
            self.current_stage
        )

        if stage is None:
            self._complete()
            return

        try:
            finished = (
                stage.update(
                    delta_time
                )
            )

        except BaseException as exc:
            self._fail(
                exc
            )

            return

        if not finished:
            return

        # ------------------------------------------------------
        # Move to next stage
        # ------------------------------------------------------

        self._stage_index += 1

        if (
            self._stage_index
            >= len(
                self._stages
            )
        ):
            self._complete()

    # ==========================================================
    # CANCEL
    # ==========================================================

    def cancel(
        self,
    ) -> None:
        if self._state in (
            LoadingState.COMPLETED,
            LoadingState.FAILED,
            LoadingState.CANCELLED,
        ):
            return

        self._state = (
            LoadingState.CANCELLED
        )

    # ==========================================================
    # INTERNAL STATE
    # ==========================================================

    def _complete(
        self,
    ) -> None:
        self._state = (
            LoadingState.COMPLETED
        )

    def _fail(
        self,
        error: BaseException,
    ) -> None:
        self._error = error

        self._state = (
            LoadingState.FAILED
        )

    # ==========================================================
    # PROGRESS
    # ==========================================================

    @property
    def progress(
        self,
    ) -> float:
        """
        Return total normalized loading progress.
        """

        if self.done:
            return 1.0

        if not self._stages:
            return (
                1.0
                if self.done
                else 0.0
            )

        total_weight = sum(
            stage.weight
            for stage in self._stages
        )

        if total_weight <= 0.0:
            return 0.0

        completed_weight = sum(
            stage.weight
            for stage in self._stages
            if stage.finished
        )

        active_weight = 0.0
        stage = self.current_stage

        if (
            stage is not None
            and not stage.finished
        ):
            active_weight = (
                stage.weight
                * stage.progress
            )

        return max(
            0.0,
            min(
                (
                    completed_weight
                    + active_weight
                )
                / total_weight,
                1.0,
            ),
        )

    @property
    def status(
        self,
    ) -> str:
        """
        Return a human-readable loading status.
        """

        if self.pending:
            return "Waiting..."

        if self.done:
            return "Complete"

        if self.failed:
            return "Failed"

        if self.cancelled:
            return "Cancelled"

        stage = (
            self.current_stage
        )

        if stage is None:
            return ""

        return stage.status

    @property
    def progress_info(
        self,
    ) -> LoadingProgress:
        """
        Return a UI-friendly loading progress snapshot.
        """

        stage = (
            self.current_stage
        )

        stage_name = (
            stage.name
            if stage is not None
            else ""
        )

        stage_index = min(
            self._stage_index,
            len(
                self._stages
            ),
        )

        stage_progress = (
            stage.progress
            if stage is not None
            else (
                1.0
                if self.done
                else 0.0
            )
        )

        return LoadingProgress(
            progress=self.progress,
            status=self.status,
            stage_name=stage_name,
            stage_index=stage_index,
            stage_count=len(
                self._stages
            ),
            stage_progress=stage_progress,
        )