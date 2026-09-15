from __future__ import annotations

import math

from nexora.core.game import Game
from nexora.nodes import Light2D, LightOccluder2D
from nexora.scene import Scene


class LightingShadowsExample(Game):
    def __init__(self) -> None:
        super().__init__(
            project_name="LightingShadowsExample",
            title="Nexora - 2D Lighting V2 Shadows",
            width=1280,
            height=720,
            target_fps=60,
            resizable=True,
            vsync=True,
        )
        self.light: Light2D | None = None
        self.fill_light: Light2D | None = None
        self.occluders: list[LightOccluder2D] = []
        self.animation_time = 0.0
        self.debug_enabled = False

    def initialize(self) -> None:
        self.scene = Scene("LightingShadowsExample")
        self.input.bind("exit", "ESCAPE")
        self.input.bind("toggle_lighting", "SPACE")
        self.input.bind("toggle_shadows", "S")

        self.renderer.lighting.set_ambient((0.12, 0.14, 0.20), 0.42)

        self.light = self.scene.create_node("WarmShadowLight", node_type=Light2D)
        self.light.transform.x = -250.0
        self.light.transform.y = -40.0
        self.light.color = (1.0, 0.44, 0.12)
        self.light.radius = 520.0
        self.light.intensity = 2.5
        self.light.falloff = 1.7
        self.light.cast_shadows = True
        self.light.shadow_strength = 0.95
        self.light.shadow_softness = 0.12
        self.light.shadow_color = (0.02, 0.02, 0.04)

        self.fill_light = self.scene.create_node("ColdFill", node_type=Light2D)
        self.fill_light.transform.x = 350.0
        self.fill_light.transform.y = 100.0
        self.fill_light.color = (0.12, 0.35, 1.0)
        self.fill_light.radius = 360.0
        self.fill_light.intensity = 1.2
        self.fill_light.falloff = 2.0
        self.fill_light.cast_shadows = True
        self.fill_light.shadow_strength = 0.7
        self.fill_light.shadow_softness = 0.04

        self._make_box("CenterWall", 0.0, -20.0, 90.0, 230.0)
        self._make_box("LowerWall", 235.0, 155.0, 180.0, 70.0)
        self._make_box("UpperWall", 200.0, -190.0, 130.0, 60.0)

        print("=" * 64)
        print(" Nexora - 2D Lighting V2 / Shadows")
        print("=" * 64)
        print("ESC   -> Exit")
        print("SPACE -> Toggle lighting")
        print("S     -> Toggle shadows")
        print("DEBUG -> Existing Nexora debug binding shows lights/occluders")

    def _make_box(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        occluder = self.scene.create_node(name, node_type=LightOccluder2D)
        occluder.transform.x = x
        occluder.transform.y = y
        half_w = width * 0.5
        half_h = height * 0.5
        occluder.set_polygon((
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h),
        ))
        self.occluders.append(occluder)

    def _set_debug(self, enabled: bool) -> None:
        self.debug_enabled = bool(enabled)
        if self.light is not None:
            self.light.debug_draw = self.debug_enabled
        if self.fill_light is not None:
            self.fill_light.debug_draw = self.debug_enabled
        for occluder in self.occluders:
            occluder.debug_draw = self.debug_enabled

    def update(self, delta_time: float) -> None:
        if self.input.action("exit").pressed:
            self.stop()
            return

        if self.input.action("toggle_lighting").pressed:
            if self.renderer.lighting.enabled:
                self.renderer.lighting.disable()
                print("Lighting: OFF")
            else:
                self.renderer.lighting.enable()
                print("Lighting: ON")

        if self.input.action("toggle_shadows").pressed:
            if self.renderer.lighting.shadows_enabled:
                self.renderer.lighting.disable_shadows()
                print("Shadows: OFF")
            else:
                self.renderer.lighting.enable_shadows()
                print("Shadows: ON")

        # Use the already configured engine debug action. Do not add another
        # hard-coded debug key here.
        if self.input.action("debug_overlay").pressed:
            self._set_debug(not self.debug_enabled)

        self.animation_time += delta_time
        if self.light is not None:
            self.light.transform.y = -40.0 + math.sin(self.animation_time * 0.7) * 65.0

        super().update(delta_time)

    def render(self, interpolation: float) -> None:
        # Neutral geometry makes the light and shadow shapes easy to inspect.
        for x in range(-540, 541, 90):
            for y in range(-270, 271, 90):
                self.renderer.rect(
                    float(x),
                    float(y),
                    68.0,
                    68.0,
                    color=(0.68, 0.69, 0.72, 1.0),
                    radius=6.0,
                    layer=0,
                )

        # Draw visible wall geometry at the same locations as the occluders.
        self.renderer.rect(0.0, -20.0, 90.0, 230.0, color=(0.20, 0.20, 0.23, 1.0), layer=10)
        self.renderer.rect(235.0, 155.0, 180.0, 70.0, color=(0.20, 0.20, 0.23, 1.0), layer=10)
        self.renderer.rect(200.0, -190.0, 130.0, 60.0, color=(0.20, 0.20, 0.23, 1.0), layer=10)

        super().render(interpolation)


if __name__ == "__main__":
    LightingShadowsExample().run()
