from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nexora.scene.manager import SceneManager
    from nexora.scene.scene import Scene


Color = tuple[
    float,
    float,
    float,
]


class SceneTransition(ABC):
    """
    Base class for asynchronous scene transitions.

    SceneManager starts the transition.

    The transition decides when the actual scene switch occurs
    and performs it through:

        SceneManager._change_scene_immediate(...)
    """

    def __init__(
        self,
    ) -> None:
        self._running = False
        self._finished = False

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def running(
        self,
    ) -> bool:
        return self._running

    @property
    def finished(
        self,
    ) -> bool:
        return self._finished

    # ==========================================================
    # START
    # ==========================================================

    def start(
        self,
        manager: SceneManager,
        target_scene: Scene,
        *,
        unload_previous: bool = False,
    ) -> None:
        if self._running:
            raise RuntimeError(
                "Scene transition is already running."
            )

        if self._finished:
            raise RuntimeError(
                "Scene transition has already finished."
            )

        self._running = True

        try:
            self._start(
                manager,
                target_scene,
                unload_previous=(
                    unload_previous
                ),
            )

        except Exception:
            self._running = False
            raise

    @abstractmethod
    def _start(
        self,
        manager: SceneManager,
        target_scene: Scene,
        *,
        unload_previous: bool,
    ) -> None:
        raise NotImplementedError

    # ==========================================================
    # FINISH
    # ==========================================================

    def _finish(
        self,
    ) -> None:
        self._running = False
        self._finished = True


class FadeSceneTransition(
    SceneTransition
):
    """
    Scene transition using the existing Camera2D fade system.

    Cameras are automatically resolved from:

        current_scene.camera
        target_scene.camera

    Explicit cameras can still be supplied if necessary.

    Flow:

        outgoing camera
            ↓
        fade_out()

            ↓

        fully black

            ↓

        switch scene

            ↓

        incoming camera
            ↓
        fade_in()

    No separate fade renderer is used.
    """

    def __init__(
        self,
        *,
        duration: float = 0.6,
        color: Color = (
            0.0,
            0.0,
            0.0,
        ),
        easing: str = "ease_in_out",
        outgoing_camera=None,
        incoming_camera=None,
    ) -> None:
        super().__init__()

        self.duration = max(
            0.0,
            float(
                duration
            ),
        )

        self.color = (
            float(
                color[0]
            ),
            float(
                color[1]
            ),
            float(
                color[2]
            ),
        )

        self.easing = str(
            easing
        )

        # ------------------------------------------------------
        # Optional explicit overrides
        # ------------------------------------------------------

        self.outgoing_camera = (
            outgoing_camera
        )

        self.incoming_camera = (
            incoming_camera
        )

        # ------------------------------------------------------
        # Runtime state
        # ------------------------------------------------------

        self._resolved_outgoing_camera = None
        self._resolved_incoming_camera = None

    # ==========================================================
    # START
    # ==========================================================

    def _start(
        self,
        manager: SceneManager,
        target_scene: Scene,
        *,
        unload_previous: bool,
    ) -> None:
        current_scene = (
            manager.active_scene
        )

        # ======================================================
        # Resolve cameras
        # ======================================================

        if self.outgoing_camera is not None:
            outgoing_camera = (
                self.outgoing_camera
            )

        elif current_scene is not None:
            outgoing_camera = (
                current_scene.camera
            )

        else:
            outgoing_camera = None

        if self.incoming_camera is not None:
            incoming_camera = (
                self.incoming_camera
            )

        else:
            incoming_camera = (
                target_scene.camera
            )

        self._resolved_outgoing_camera = (
            outgoing_camera
        )

        self._resolved_incoming_camera = (
            incoming_camera
        )

        # ======================================================
        # Prepare incoming scene
        # ======================================================
        #
        # Put the incoming camera immediately at full fade before
        # the actual scene switch.
        #
        # This guarantees there cannot be a one-frame flash of
        # the new scene during the switch.
        # ======================================================

        if incoming_camera is not None:
            incoming_camera.fade_to(
                1.0,
                duration=0.0,
                color=self.color,
                easing=self.easing,
            )

        # ======================================================
        # No current scene
        # ======================================================

        if current_scene is None:
            manager._change_scene_immediate(
                target_scene.name,
                unload_previous=False,
            )

            self._begin_fade_in()

            return

        # ======================================================
        # No outgoing camera
        # ======================================================

        if outgoing_camera is None:
            manager._change_scene_immediate(
                target_scene.name,
                unload_previous=(
                    unload_previous
                ),
            )

            self._begin_fade_in()

            return

        # ======================================================
        # Fade out
        # ======================================================

        fade_out_duration = (
            self.duration
            * 0.5
        )

        # ------------------------------------------------------
        # Zero-duration transition
        # ------------------------------------------------------

        if fade_out_duration <= 0.0:
            self._switch_scene(
                manager,
                target_scene,
                unload_previous,
            )

            return

        outgoing_camera.fade_out(
            duration=fade_out_duration,
            color=self.color,
            easing=self.easing,
            on_complete=lambda: (
                self._switch_scene(
                    manager,
                    target_scene,
                    unload_previous,
                )
            ),
        )

    # ==========================================================
    # SWITCH
    # ==========================================================

    def _switch_scene(
        self,
        manager: SceneManager,
        target_scene: Scene,
        unload_previous: bool,
    ) -> None:
        manager._change_scene_immediate(
            target_scene.name,
            unload_previous=(
                unload_previous
            ),
        )

        self._begin_fade_in()

    # ==========================================================
    # FADE IN
    # ==========================================================

    def _begin_fade_in(
        self,
    ) -> None:
        camera = (
            self._resolved_incoming_camera
        )

        # ------------------------------------------------------
        # Scene has no camera
        # ------------------------------------------------------

        if camera is None:
            self._finish()
            return

        fade_in_duration = (
            self.duration
            * 0.5
        )

        # ------------------------------------------------------
        # Instant transition
        # ------------------------------------------------------

        if fade_in_duration <= 0.0:
            camera.fade_to(
                0.0,
                duration=0.0,
                color=self.color,
                easing=self.easing,
            )

            self._finish()
            return

        # ------------------------------------------------------
        # Fade in
        # ------------------------------------------------------

        camera.fade_in(
            duration=fade_in_duration,
            easing=self.easing,
            on_complete=(
                self._finish
            ),
        )