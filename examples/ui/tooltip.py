from __future__ import annotations

from nexora import Game
from nexora.nodes import Tooltip
from nexora.scene import Scene


class TooltipExample(Game):
    """
    Nexora Tooltip example.

    Tests:

        - hover detection
        - tooltip delay
        - mouse following
        - automatic edge flipping
        - viewport clamping
        - fade in / out

    Controls:

        Mouse
            Hover over the colored boxes.

        F
            Toggle follow_mouse.

        1
            No show delay.

        2
            0.35 second show delay.

        3
            1.0 second show delay.

        ESC
            Exit.
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - Tooltip Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        self.tooltip: Tooltip | None = None

        # ======================================================
        # Hover regions
        #
        # Screen coordinates:
        #
        #     x, y, width, height, title, description, color
        #
        # x/y represent the center of the rectangle.
        # ======================================================

        self.regions = [
            (
                170.0,
                150.0,
                240.0,
                110.0,
                "Rostiges Schwert",
                (
                    "Ein altes und stark "
                    "beschädigtes Schwert."
                ),
                (
                    0.35,
                    0.42,
                    0.55,
                    1.0,
                ),
            ),
            (
                640.0,
                180.0,
                260.0,
                120.0,
                "Heiltrank",
                (
                    "Stellt einen Teil deiner "
                    "Gesundheit wieder her."
                ),
                (
                    0.25,
                    0.65,
                    0.35,
                    1.0,
                ),
            ),
            (
                1110.0,
                150.0,
                240.0,
                110.0,
                "Seltsames Artefakt",
                (
                    "Niemand weiß genau, "
                    "woher dieses Objekt stammt."
                ),
                (
                    0.55,
                    0.30,
                    0.65,
                    1.0,
                ),
            ),
            (
                170.0,
                580.0,
                240.0,
                110.0,
                "Schrott",
                (
                    "Kann beim Crafting für "
                    "einfache Bauteile verwendet werden."
                ),
                (
                    0.55,
                    0.40,
                    0.20,
                    1.0,
                ),
            ),
            (
                640.0,
                550.0,
                260.0,
                120.0,
                "Energiezelle",
                (
                    "Eine noch teilweise "
                    "geladene Energiequelle."
                ),
                (
                    0.20,
                    0.55,
                    0.75,
                    1.0,
                ),
            ),
            (
                1110.0,
                580.0,
                240.0,
                110.0,
                "Gefährliches Material",
                (
                    "Vorsicht. Der Inhalt "
                    "dieses Behälters ist instabil."
                ),
                (
                    0.75,
                    0.25,
                    0.20,
                    1.0,
                ),
            ),
        ]

        self._hovered_index: int | None = None

    # ==========================================================
    # Initialize
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Input
        # ------------------------------------------------------

        self.input.bind(
            "toggle_follow",
            "F",
        )

        self.input.bind(
            "delay_none",
            "1",
        )

        self.input.bind(
            "delay_normal",
            "2",
        )

        self.input.bind(
            "delay_long",
            "3",
        )

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = Scene(
            "TooltipExample"
        )

        self.scene = scene

        # ------------------------------------------------------
        # Camera
        # ------------------------------------------------------

        self.renderer.camera.set_position(
            0.0,
            0.0,
        )

        self.renderer.camera.set_zoom(
            1.0
        )

        # ------------------------------------------------------
        # Tooltip
        # ------------------------------------------------------

        self.tooltip = Tooltip(
            "Tooltip",
            scene.world,
            self.renderer,
        )

        self.tooltip.follow_mouse = True

        self.tooltip.width = 340.0
        self.tooltip.height = 110.0

        self.tooltip.offset_x = 20.0
        self.tooltip.offset_y = 20.0

        self.tooltip.margin = 12.0

        self.tooltip.delay = 0.35

        self.tooltip.fade_in_duration = 0.16
        self.tooltip.fade_out_duration = 0.12

        scene.add_node(
            self.tooltip
        )

        # ------------------------------------------------------
        # Console
        # ------------------------------------------------------

        self._print_controls()

    # ==========================================================
    # Console
    # ==========================================================

    def _print_controls(
        self,
    ) -> None:
        print()
        print("=" * 62)
        print(" Nexora Tooltip Example")
        print("=" * 62)
        print()
        print("Hover over the colored boxes.")
        print()
        print("F    Toggle mouse following")
        print()
        print("1    Tooltip delay: 0.0")
        print("2    Tooltip delay: 0.35")
        print("3    Tooltip delay: 1.0")
        print()
        print("ESC  Exit")
        print()

    # ==========================================================
    # Mouse
    # ==========================================================

    def _mouse_position(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        """
        Return mouse position in normal viewport coordinates.

        InputManager already exposes mouse_position directly.
        """

        x, y = (
            self.input.mouse_position
        )

        return (
            float(x),
            float(y),
        )

    # ==========================================================
    # Hover
    # ==========================================================

    @staticmethod
    def _point_inside(
        point_x: float,
        point_y: float,
        center_x: float,
        center_y: float,
        width: float,
        height: float,
    ) -> bool:
        half_width = (
            width
            * 0.5
        )

        half_height = (
            height
            * 0.5
        )

        return (
            center_x - half_width
            <= point_x
            <= center_x + half_width
            and
            center_y - half_height
            <= point_y
            <= center_y + half_height
        )

    def _find_hovered_region(
        self,
        mouse_x: float,
        mouse_y: float,
    ) -> int | None:
        for index, region in enumerate(
            self.regions
        ):
            (
                x,
                y,
                width,
                height,
                _title,
                _description,
                _color,
            ) = region

            if self._point_inside(
                mouse_x,
                mouse_y,
                x,
                y,
                width,
                height,
            ):
                return index

        return None

    # ==========================================================
    # Tooltip handling
    # ==========================================================

    def _update_tooltip(
        self,
        mouse_x: float,
        mouse_y: float,
    ) -> None:
        tooltip = (
            self.tooltip
        )

        if tooltip is None:
            return

        # ------------------------------------------------------
        # Mouse position
        # ------------------------------------------------------

        tooltip.set_mouse_position(
            mouse_x,
            mouse_y,
        )

        # ------------------------------------------------------
        # Hover
        # ------------------------------------------------------

        hovered = (
            self._find_hovered_region(
                mouse_x,
                mouse_y,
            )
        )

        # ------------------------------------------------------
        # Same region
        #
        # Do NOT call show() every frame because that would
        # continuously reset the tooltip delay.
        # ------------------------------------------------------

        if hovered == self._hovered_index:
            if (
                hovered is not None
                and not tooltip.follow_mouse
            ):
                tooltip.set_position(
                    mouse_x,
                    mouse_y,
                )

            return

        # ------------------------------------------------------
        # Region changed
        # ------------------------------------------------------

        self._hovered_index = hovered

        if hovered is None:
            tooltip.hide()
            return

        (
            _x,
            _y,
            _width,
            _height,
            title,
            description,
            _color,
        ) = self.regions[
            hovered
        ]

        tooltip.show(
            title,
            description=description,
            x=mouse_x,
            y=mouse_y,
        )

    # ==========================================================
    # Input handling
    # ==========================================================

    def _handle_input(
        self,
    ) -> None:
        tooltip = (
            self.tooltip
        )

        if tooltip is None:
            return

        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        # ------------------------------------------------------
        # Follow mouse
        # ------------------------------------------------------

        if self.input.action(
            "toggle_follow"
        ).pressed:
            tooltip.follow_mouse = (
                not tooltip.follow_mouse
            )

            print(
                "follow_mouse:",
                tooltip.follow_mouse,
            )

        # ------------------------------------------------------
        # Delay
        # ------------------------------------------------------

        if self.input.action(
            "delay_none"
        ).pressed:
            tooltip.delay = 0.0

            print(
                "Tooltip delay: 0.0"
            )

        if self.input.action(
            "delay_normal"
        ).pressed:
            tooltip.delay = 0.35

            print(
                "Tooltip delay: 0.35"
            )

        if self.input.action(
            "delay_long"
        ).pressed:
            tooltip.delay = 1.0

            print(
                "Tooltip delay: 1.0"
            )

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        self._handle_input()

        mouse_x, mouse_y = (
            self._mouse_position()
        )

        self._update_tooltip(
            mouse_x,
            mouse_y,
        )

        super().update(
            delta_time
        )

    # ==========================================================
    # Screen rectangle helper
    # ==========================================================

    def _screen_rect(
        self,
        screen_x: float,
        screen_y: float,
        width: float,
        height: float,
        color,
    ) -> None:
        """
        Draw rectangle at normal top-left based screen
        coordinates while compensating for the camera.
        """

        camera = (
            self.renderer.camera
        )

        zoom = max(
            float(
                camera.zoom
            ),
            0.0001,
        )

        center_x = (
            float(
                self.renderer.width
            )
            * 0.5
        )

        center_y = (
            float(
                self.renderer.height
            )
            * 0.5
        )

        shake_x = float(
            getattr(
                camera,
                "shake_x",
                0.0,
            )
        )

        shake_y = float(
            getattr(
                camera,
                "shake_y",
                0.0,
            )
        )

        world_x = (
            float(
                camera.x
            )
            - shake_x
            + (
                screen_x
                - center_x
            )
            / zoom
        )

        world_y = (
            float(
                camera.y
            )
            - shake_y
            + (
                screen_y
                - center_y
            )
            / zoom
        )

        self.renderer.rect(
            world_x,
            world_y,
            width / zoom,
            height / zoom,
            color=color,
            radius=(
                8.0
                / zoom
            ),
            origin=(
                0.5,
                0.5,
            ),
        )

    # ==========================================================
    # Screen text helper
    # ==========================================================

    def _screen_text(
        self,
        text: str,
        screen_x: float,
        screen_y: float,
        *,
        scale: float = 1.0,
    ) -> None:
        """
        Nexora GPUTextRenderer currently uses centered
        screen coordinates.
        """

        x = (
            screen_x
            - float(
                self.renderer.width
            )
            * 0.5
        )

        y = (
            screen_y
            - float(
                self.renderer.height
            )
            * 0.5
        )

        self.renderer.text(
            text,
            x,
            y,
            scale=scale,
        )

    # ==========================================================
    # Render
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        # ------------------------------------------------------
        # Background
        # ------------------------------------------------------

        self._screen_rect(
            self.renderer.width
            * 0.5,
            self.renderer.height
            * 0.5,
            self.renderer.width,
            self.renderer.height,
            (
                0.035,
                0.04,
                0.055,
                1.0,
            ),
        )

        # ------------------------------------------------------
        # Header
        # ------------------------------------------------------

        self._screen_text(
            "Nexora Tooltip Test",
            32.0,
            40.0,
            scale=1.15,
        )

        self._screen_text(
            "Hover over an item",
            32.0,
            72.0,
            scale=0.8,
        )

        # ------------------------------------------------------
        # Regions
        # ------------------------------------------------------

        for index, region in enumerate(
            self.regions
        ):
            (
                x,
                y,
                width,
                height,
                title,
                _description,
                color,
            ) = region

            # --------------------------------------------------
            # Highlight hovered item
            # --------------------------------------------------

            if index == self._hovered_index:
                render_width = (
                    width
                    + 8.0
                )

                render_height = (
                    height
                    + 8.0
                )

            else:
                render_width = width
                render_height = height

            self._screen_rect(
                x,
                y,
                render_width,
                render_height,
                color,
            )

            # --------------------------------------------------
            # Label
            # --------------------------------------------------

            text_x = (
                x
                - width
                * 0.5
                + 16.0
            )

            self._screen_text(
                title,
                text_x,
                y,
                scale=0.75,
            )

        # ------------------------------------------------------
        # Scene nodes
        #
        # Tooltip is rendered here through the scene tree.
        # ------------------------------------------------------

        super().render(
            interpolation
        )


if __name__ == "__main__":
    TooltipExample().run()