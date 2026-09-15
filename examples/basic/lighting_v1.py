from __future__ import annotations

import math

from nexora.core.game import Game
from nexora.nodes import Light2D
from nexora.scene import Scene


class LightingExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="LightingExample",
            title="Nexora - 2D Lighting V1",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )

        self.light_a: Light2D | None = None
        self.light_b: Light2D | None = None

        self.animation_time = 0.0
        self.light_debug_enabled = False

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(self) -> None:
        self.scene = Scene(
            "LightingExample"
        )

        # ------------------------------------------------------
        # Example-specific bindings
        # ------------------------------------------------------

        self.input.bind(
            "exit",
            "ESCAPE",
        )

        self.input.bind(
            "toggle_lighting",
            "SPACE",
        )

        # IMPORTANT:
        #
        # debug_overlay is NOT bound here.
        #
        # It comes from Nexora's global/default input bindings.
        # That means changing the engine debug key automatically
        # changes the key used here too.

        # ------------------------------------------------------
        # Ambient lighting
        # ------------------------------------------------------

        self.renderer.lighting.set_ambient(
            (
                0.22,
                0.25,
                0.32,
            ),
            0.45,
        )

        # ------------------------------------------------------
        # Warm light
        # ------------------------------------------------------

        self.light_a = (
            self.scene.create_node(
                "WarmLamp",
                node_type=Light2D,
            )
        )

        self.light_a.transform.x = -180.0
        self.light_a.transform.y = 0.0

        self.light_a.color = (
            1.0,
            0.45,
            0.12,
        )

        self.light_a.radius = 260.0
        self.light_a.intensity = 2.2
        self.light_a.falloff = 2.0

        self.light_a.flicker_enabled = True
        self.light_a.flicker_strength = 0.10
        self.light_a.flicker_speed = 17.0

        # Debug starts disabled.
        self.light_a.debug_draw = False

        # ------------------------------------------------------
        # Cold light
        # ------------------------------------------------------

        self.light_b = (
            self.scene.create_node(
                "ColdLamp",
                node_type=Light2D,
            )
        )

        self.light_b.transform.x = 180.0
        self.light_b.transform.y = 20.0

        self.light_b.color = (
            0.15,
            0.45,
            1.0,
        )

        self.light_b.radius = 300.0
        self.light_b.intensity = 1.8
        self.light_b.falloff = 1.5

        self.light_b.pulse_enabled = True
        self.light_b.pulse_amount = 0.12
        self.light_b.pulse_speed = 0.6

        self.light_b.debug_draw = False

        # ------------------------------------------------------
        # Info
        # ------------------------------------------------------

        print("=" * 60)
        print(" Nexora - 2D Lighting V1")
        print("=" * 60)
        print()
        print("ESC   -> Exit")
        print("SPACE -> Toggle lighting")
        print(
            "DEBUG -> Toggle global debug overlay "
            "+ Light2D debug"
        )
        print()

    # ==========================================================
    # LIGHT DEBUG
    # ==========================================================

    def _set_light_debug(
        self,
        enabled: bool,
    ) -> None:
        self.light_debug_enabled = bool(
            enabled
        )

        if self.light_a is not None:
            self.light_a.debug_draw = (
                self.light_debug_enabled
            )

        if self.light_b is not None:
            self.light_b.debug_draw = (
                self.light_debug_enabled
            )

        print(
            "Light Debug:",
            "ON"
            if self.light_debug_enabled
            else "OFF",
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if (
            self.input
            .action("exit")
            .pressed
        ):
            self.stop()
            return

        # ------------------------------------------------------
        # Lighting toggle
        # ------------------------------------------------------

        if (
            self.input
            .action("toggle_lighting")
            .pressed
        ):
            if (
                self.renderer
                .lighting
                .enabled
            ):
                self.renderer.lighting.disable()

                print(
                    "Lighting: OFF"
                )

            else:
                self.renderer.lighting.enable()

                print(
                    "Lighting: ON"
                )

        # ------------------------------------------------------
        # Light debug toggle
        #
        # Uses Nexora's EXISTING global debug binding.
        #
        # We intentionally do NOT call input.bind() for it.
        # ------------------------------------------------------

        if (
            self.input
            .action("physics_debug")
            .pressed
        ):
            self._set_light_debug(
                not self.light_debug_enabled
            )

        # ------------------------------------------------------
        # Animation
        # ------------------------------------------------------

        self.animation_time += (
            delta_time
        )

        # Warm light moves slightly vertically.
        if self.light_a is not None:
            self.light_a.transform.y = (
                math.sin(
                    self.animation_time
                    * 0.8
                )
                * 30.0
            )

        # Cold light has slower movement.
        if self.light_b is not None:
            self.light_b.transform.y = (
                20.0
                + math.sin(
                    self.animation_time
                    * 0.5
                )
                * 25.0
            )

        super().update(
            delta_time
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        # ------------------------------------------------------
        # Neutral test geometry
        #
        # This makes ambient light, color and falloff easy to
        # inspect.
        # ------------------------------------------------------

        for x in range(
            -500,
            501,
            100,
        ):
            for y in range(
                -250,
                251,
                100,
            ):
                self.renderer.rect(
                    float(x),
                    float(y),
                    72.0,
                    72.0,
                    color=(
                        0.72,
                        0.72,
                        0.72,
                        1.0,
                    ),
                    radius=8.0,
                    layer=0,
                )

        # Scene rendering submits Light2D nodes and their
        # optional debug geometry.
        super().render(
            interpolation
        )


if __name__ == "__main__":
    LightingExample().run()