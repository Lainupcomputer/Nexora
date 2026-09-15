from __future__ import annotations

from dataclasses import dataclass

from .light import LightSnapshot


@dataclass(slots=True)
class ScreenLight:
    x: float
    y: float
    radius: float
    intensity: float
    color: tuple[float, float, float]
    falloff: float


class LightingSystem:
    """Per-renderer 2D lighting collector and environment state.

    Light2D nodes submit world-space snapshots during scene rendering.
    At the end of the frame this service converts them into screen-space
    lights and forwards them to the fullscreen post-process pass.
    """

    MAX_LIGHTS = 32

    def __init__(
        self,
        *,
        max_lights: int = MAX_LIGHTS,
    ) -> None:
        self.enabled = False

        self.ambient_color: tuple[
            float,
            float,
            float,
        ] = (
            1.0,
            1.0,
            1.0,
        )

        self.ambient_intensity = 1.0

        self.visible_mask = (
            0xFFFFFFFF
        )

        self.max_lights = max(
            1,
            min(
                int(max_lights),
                self.MAX_LIGHTS,
            ),
        )

        self._submitted: list[
            LightSnapshot
        ] = []

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _clamp01(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    # ==========================================================
    # STATE
    # ==========================================================

    @property
    def light_count(
        self,
    ) -> int:
        return len(
            self._submitted
        )

    def enable(
        self,
    ) -> None:
        self.enabled = True

    def disable(
        self,
    ) -> None:
        self.enabled = False

    # ==========================================================
    # AMBIENT
    # ==========================================================

    def set_ambient(
        self,
        color: tuple[
            float,
            float,
            float,
        ],
        intensity: float = 1.0,
    ) -> None:
        if len(color) != 3:
            raise ValueError(
                "Ambient color must contain exactly three values"
            )

        self.ambient_color = tuple(
            self._clamp01(v)
            for v in color
        )

        self.ambient_intensity = max(
            0.0,
            float(intensity),
        )

        # Setting ambient lighting is an explicit lighting action.
        # It is fine to enable the lighting system here.
        self.enabled = True

    # ==========================================================
    # FRAME
    # ==========================================================

    def begin_frame(
        self,
    ) -> None:
        self._submitted.clear()

    # ==========================================================
    # LIGHT SUBMISSION
    # ==========================================================

    def submit(
        self,
        light: LightSnapshot,
    ) -> bool:
        # ------------------------------------------------------
        # MASK FILTER
        # ------------------------------------------------------

        if (
            light.mask
            & self.visible_mask
            == 0
        ):
            return False

        # ------------------------------------------------------
        # MAX LIGHT LIMIT
        # ------------------------------------------------------

        if (
            len(self._submitted)
            >= self.max_lights
        ):
            return False

        # ------------------------------------------------------
        # STORE LIGHT
        # ------------------------------------------------------
        #
        # IMPORTANT:
        #
        # submit() must NOT enable the lighting system.
        #
        # Otherwise every Light2D would immediately reactivate
        # lighting after lighting.disable() was called.
        # ------------------------------------------------------

        self._submitted.append(
            light
        )

        return True

    # ==========================================================
    # SCREEN LIGHTS
    # ==========================================================

    def screen_lights(
        self,
        camera,
        width: int,
        height: int,
    ) -> tuple[
        ScreenLight,
        ...,
    ]:
        if (
            width <= 0
            or height <= 0
        ):
            return ()

        zoom = max(
            float(
                getattr(
                    camera,
                    "zoom",
                    1.0,
                )
            ),
            0.0001,
        )

        result: list[
            ScreenLight
        ] = []

        for light in (
            self._submitted[
                : self.max_lights
            ]
        ):
            sx, sy = (
                camera.world_to_screen(
                    light.x,
                    light.y,
                    width,
                    height,
                )
            )

            radius = max(
                light.radius
                * zoom,
                0.0,
            )

            if (
                radius <= 0.0
                or light.intensity
                <= 0.0
            ):
                continue

            # --------------------------------------------------
            # VIEWPORT CULLING
            # --------------------------------------------------

            if (
                sx + radius < 0.0
                or sx - radius > width
            ):
                continue

            if (
                sy + radius < 0.0
                or sy - radius > height
            ):
                continue

            result.append(
                ScreenLight(
                    x=float(sx),
                    y=float(sy),
                    radius=float(
                        radius
                    ),
                    intensity=float(
                        light.intensity
                    ),
                    color=tuple(
                        float(v)
                        for v
                        in light.color
                    ),
                    falloff=float(
                        light.falloff
                    ),
                )
            )

        return tuple(
            result
        )

    # ==========================================================
    # APPLY
    # ==========================================================

    def apply(
        self,
        post_process,
        camera,
        width: int,
        height: int,
    ) -> None:
        # ------------------------------------------------------
        # LIGHTING DISABLED
        # ------------------------------------------------------

        if not self.enabled:
            post_process.set_lighting(
                enabled=False,
                ambient_color=(
                    1.0,
                    1.0,
                    1.0,
                ),
                ambient_intensity=1.0,
                lights=(),
            )

            return

        # ------------------------------------------------------
        # LIGHTING ENABLED
        # ------------------------------------------------------
        #
        # Lighting is implemented as part of the existing
        # fullscreen post-process pass.
        # ------------------------------------------------------

        post_process.enable()

        post_process.set_lighting(
            enabled=True,
            ambient_color=(
                self.ambient_color
            ),
            ambient_intensity=(
                self.ambient_intensity
            ),
            lights=(
                self.screen_lights(
                    camera,
                    width,
                    height,
                )
            ),
        )