from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes.node import Node


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


Color = tuple[
    float,
    float,
    float,
    float,
]


class Tooltip(Node):
    """
    Screen-space tooltip node.

    Features:

        - title
        - description
        - automatic word wrapping
        - automatic tooltip height
        - delayed appearance
        - fade in / fade out
        - automatic screen-edge flipping
        - viewport clamping
        - mouse-follow mode
        - manual positioning
        - configurable size and padding

    Example:

        tooltip = Tooltip(
            "Tooltip",
            world,
            renderer,
        )

        tooltip.show(
            "Rostiges Schwert",
            description=(
                "Ein altes und stark beschädigtes Schwert."
            ),
            x=mouse_x,
            y=mouse_y,
        )
    """

    def __init__(
        self,
        name: str,
        world,
        renderer: Renderer,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.renderer = renderer

        # ======================================================
        # State
        # ======================================================

        self.enabled: bool = True

        self.visible: bool = False

        self._target_visible: bool = False

        # ======================================================
        # Content
        # ======================================================

        self.title: str = ""

        self.description: str = ""

        # ======================================================
        # Position
        # ======================================================

        self.x: float = 0.0
        self.y: float = 0.0

        self.offset_x: float = 18.0
        self.offset_y: float = 18.0

        # ======================================================
        # Size
        # ======================================================

        self.width: float = 320.0

        # Minimum height.
        self.height: float = 110.0

        self.padding: float = 18.0

        self.margin: float = 12.0

        self.corner_radius: float = 8.0

        # ======================================================
        # Text
        # ======================================================

        self.title_scale: float = 1.0

        self.description_scale: float = 0.82

        self.title_line_height: float = 24.0

        self.description_line_height: float = 22.0

        self.title_description_spacing: float = 10.0

        # ======================================================
        # Appearance
        # ======================================================

        self.background_color: Color = (
            0.055,
            0.055,
            0.07,
            0.97,
        )

        self.border_color: Color = (
            0.25,
            0.25,
            0.30,
            1.0,
        )

        self.title_color: Color = (
            1.0,
            1.0,
            1.0,
            1.0,
        )

        self.description_color: Color = (
            0.80,
            0.80,
            0.84,
            1.0,
        )

        self.border_width: float = 2.0

        # ======================================================
        # Timing
        # ======================================================

        self.delay: float = 0.35

        self.fade_in_duration: float = 0.16

        self.fade_out_duration: float = 0.12

        self._delay_elapsed: float = 0.0

        self._fade_elapsed: float = 0.0

        self.alpha: float = 0.0

        # ======================================================
        # Mouse following
        # ======================================================

        self.follow_mouse: bool = False

        self.mouse_x: float = 0.0
        self.mouse_y: float = 0.0

    # ==========================================================
    # Utility
    # ==========================================================

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(
                maximum,
                float(value),
            ),
        )

    @staticmethod
    def _ease_out(
        value: float,
    ) -> float:
        value = max(
            0.0,
            min(
                1.0,
                value,
            ),
        )

        inverse = (
            1.0
            - value
        )

        return (
            1.0
            - inverse
            * inverse
            * inverse
        )

    # ==========================================================
    # Show
    # ==========================================================

    def show(
        self,
        title: str,
        *,
        description: str = "",
        x: float | None = None,
        y: float | None = None,
        delay: float | None = None,
    ) -> None:
        """
        Show a tooltip.

        x/y use top-left based screen coordinates.
        """

        self.title = str(
            title
        )

        self.description = str(
            description
        )

        if x is not None:
            self.x = float(
                x
            )

        if y is not None:
            self.y = float(
                y
            )

        if delay is not None:
            self.delay = max(
                0.0,
                float(
                    delay
                ),
            )

        self._delay_elapsed = 0.0

        self._fade_elapsed = 0.0

        self._target_visible = True

        if self.delay <= 0.0:
            self.visible = True

    # ==========================================================
    # Hide
    # ==========================================================

    def hide(
        self,
    ) -> None:
        """
        Fade tooltip out.
        """

        self._target_visible = False

        self._fade_elapsed = 0.0

    def clear(
        self,
    ) -> None:
        """
        Immediately hide and clear tooltip.
        """

        self.visible = False

        self._target_visible = False

        self.alpha = 0.0

        self._delay_elapsed = 0.0
        self._fade_elapsed = 0.0

        self.title = ""
        self.description = ""

    # ==========================================================
    # Position
    # ==========================================================

    def set_position(
        self,
        x: float,
        y: float,
    ) -> None:
        self.x = float(
            x
        )

        self.y = float(
            y
        )

    def set_mouse_position(
        self,
        x: float,
        y: float,
    ) -> None:
        """
        Update mouse position used when follow_mouse=True.
        """

        self.mouse_x = float(
            x
        )

        self.mouse_y = float(
            y
        )

    # ==========================================================
    # Word wrapping
    # ==========================================================

    def _wrap_text(
        self,
        text: str,
        max_width: float,
        *,
        scale: float,
    ) -> list[str]:
        """
        Wrap text into lines that fit inside max_width.
        """

        text = str(
            text
        ).strip()

        if not text:
            return []

        words = text.split()

        if not words:
            return []

        lines: list[str] = []

        current_line = (
            words[0]
        )

        for word in words[1:]:
            candidate = (
                current_line
                + " "
                + word
            )

            width, _ = (
                self.renderer.text_measure(
                    candidate,
                    scale=scale,
                )
            )

            if width <= max_width:
                current_line = (
                    candidate
                )

            else:
                lines.append(
                    current_line
                )

                current_line = word

        lines.append(
            current_line
        )

        return lines

    # ==========================================================
    # Layout
    # ==========================================================

    def _layout(
        self,
    ) -> tuple[
        list[str],
        list[str],
        float,
    ]:
        """
        Calculate wrapped text and resulting tooltip height.

        Returns:

            title_lines
            description_lines
            render_height
        """

        max_text_width = max(
            1.0,
            self.width
            - self.padding
            * 2.0,
        )

        title_lines = (
            self._wrap_text(
                self.title,
                max_text_width,
                scale=self.title_scale,
            )
        )

        description_lines = (
            self._wrap_text(
                self.description,
                max_text_width,
                scale=self.description_scale,
            )
        )

        content_height = (
            self.padding
            * 2.0
        )

        # ------------------------------------------------------
        # Title
        # ------------------------------------------------------

        if title_lines:
            content_height += (
                len(
                    title_lines
                )
                * self.title_line_height
            )

        # ------------------------------------------------------
        # Description spacing
        # ------------------------------------------------------

        if (
            title_lines
            and description_lines
        ):
            content_height += (
                self.title_description_spacing
            )

        # ------------------------------------------------------
        # Description
        # ------------------------------------------------------

        if description_lines:
            content_height += (
                len(
                    description_lines
                )
                * self.description_line_height
            )

        render_height = max(
            self.height,
            content_height,
        )

        return (
            title_lines,
            description_lines,
            render_height,
        )

    # ==========================================================
    # Desired position
    # ==========================================================

    def _desired_position(
        self,
        render_height: float,
    ) -> tuple[
        float,
        float,
    ]:
        if self.follow_mouse:
            base_x = self.mouse_x
            base_y = self.mouse_y

        else:
            base_x = self.x
            base_y = self.y

        target_x = (
            base_x
            + self.offset_x
        )

        target_y = (
            base_y
            + self.offset_y
        )

        screen_width = float(
            self.renderer.width
        )

        screen_height = float(
            self.renderer.height
        )

        # ------------------------------------------------------
        # Flip horizontally
        # ------------------------------------------------------

        if (
            target_x
            + self.width
            > screen_width
            - self.margin
        ):
            target_x = (
                base_x
                - self.offset_x
                - self.width
            )

        # ------------------------------------------------------
        # Flip vertically
        # ------------------------------------------------------

        if (
            target_y
            + render_height
            > screen_height
            - self.margin
        ):
            target_y = (
                base_y
                - self.offset_y
                - render_height
            )

        # ------------------------------------------------------
        # Clamp horizontally
        # ------------------------------------------------------

        max_x = max(
            self.margin,
            screen_width
            - self.width
            - self.margin,
        )

        target_x = self._clamp(
            target_x,
            self.margin,
            max_x,
        )

        # ------------------------------------------------------
        # Clamp vertically
        # ------------------------------------------------------

        max_y = max(
            self.margin,
            screen_height
            - render_height
            - self.margin,
        )

        target_y = self._clamp(
            target_y,
            self.margin,
            max_y,
        )

        return (
            target_x,
            target_y,
        )

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self.enabled:
            return

        # ------------------------------------------------------
        # Show requested
        # ------------------------------------------------------

        if self._target_visible:
            if not self.visible:
                self._delay_elapsed += (
                    delta_time
                )

                if (
                    self._delay_elapsed
                    >= self.delay
                ):
                    self.visible = True

                    self._fade_elapsed = 0.0

            if self.visible:
                if self.fade_in_duration <= 0.0:
                    self.alpha = 1.0

                else:
                    self._fade_elapsed += (
                        delta_time
                    )

                    progress = min(
                        self._fade_elapsed
                        / self.fade_in_duration,
                        1.0,
                    )

                    self.alpha = (
                        self._ease_out(
                            progress
                        )
                    )

        # ------------------------------------------------------
        # Hide requested
        # ------------------------------------------------------

        else:
            if self.visible:
                if self.fade_out_duration <= 0.0:
                    self.alpha = 0.0

                    self.visible = False

                else:
                    self._fade_elapsed += (
                        delta_time
                    )

                    progress = min(
                        self._fade_elapsed
                        / self.fade_out_duration,
                        1.0,
                    )

                    self.alpha = (
                        1.0
                        - progress
                    )

                    if progress >= 1.0:
                        self.alpha = 0.0

                        self.visible = False

    # ==========================================================
    # Screen-space conversion
    # ==========================================================

    def _screen_to_world(
        self,
        x: float,
        y: float,
    ) -> tuple[
        float,
        float,
    ]:
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
                x
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
                y
                - center_y
            )
            / zoom
        )

        return (
            world_x,
            world_y,
        )

    # ==========================================================
    # Color
    # ==========================================================

    @staticmethod
    def _with_alpha(
        color: Color,
        alpha: float,
    ) -> Color:
        return (
            color[0],
            color[1],
            color[2],
            color[3]
            * alpha,
        )

    # ==========================================================
    # Rectangle rendering
    # ==========================================================

    def _render_rect(
        self,
        screen_x: float,
        screen_y: float,
        width: float,
        height: float,
        *,
        color: Color,
        radius: float = 0.0,
    ) -> None:
        camera = (
            self.renderer.camera
        )

        zoom = max(
            float(
                camera.zoom
            ),
            0.0001,
        )

        world_x, world_y = (
            self._screen_to_world(
                screen_x,
                screen_y,
            )
        )

        self.renderer.rect(
            world_x,
            world_y,
            width / zoom,
            height / zoom,
            color=color,
            radius=(
                radius
                / zoom
            ),
            origin=(
                0.5,
                0.5,
            ),
        )

    # ==========================================================
    # Text rendering
    # ==========================================================

    def _render_text(
        self,
        text: str,
        screen_x: float,
        screen_y: float,
        *,
        scale: float,
    ) -> None:
        """
        GPUTextRenderer uses centered screen coordinates.

        0,0 = viewport center.
        """

        x = (
            float(
                screen_x
            )
            - float(
                self.renderer.width
            )
            * 0.5
        )

        y = (
            float(
                screen_y
            )
            - float(
                self.renderer.height
            )
            * 0.5
        )

        self.renderer.text(
            text,
            x,
            y,
            scale=float(
                scale
            ),
        )

    # ==========================================================
    # Render
    # ==========================================================

    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        if not self.enabled:
            return

        if not self.visible:
            return

        if self.alpha <= 0.0:
            return

        # ------------------------------------------------------
        # Layout
        # ------------------------------------------------------

        (
            title_lines,
            description_lines,
            render_height,
        ) = self._layout()

        # ------------------------------------------------------
        # Position
        # ------------------------------------------------------

        x, y = (
            self._desired_position(
                render_height
            )
        )

        center_x = (
            x
            + self.width
            * 0.5
        )

        center_y = (
            y
            + render_height
            * 0.5
        )

        # ------------------------------------------------------
        # Border
        # ------------------------------------------------------

        if self.border_width > 0.0:
            self._render_rect(
                center_x,
                center_y,
                self.width
                + self.border_width
                * 2.0,
                render_height
                + self.border_width
                * 2.0,
                color=self._with_alpha(
                    self.border_color,
                    self.alpha,
                ),
                radius=(
                    self.corner_radius
                    + self.border_width
                ),
            )

        # ------------------------------------------------------
        # Background
        # ------------------------------------------------------

        self._render_rect(
            center_x,
            center_y,
            self.width,
            render_height,
            color=self._with_alpha(
                self.background_color,
                self.alpha,
            ),
            radius=self.corner_radius,
        )

        # ------------------------------------------------------
        # Text origin
        # ------------------------------------------------------

        text_x = (
            x
            + self.padding
        )

        current_y = (
            y
            + self.padding
        )

        # ------------------------------------------------------
        # Title
        # ------------------------------------------------------

        for line in title_lines:
            # renderer.text currently uses the supplied point
            # as the text origin, therefore move to an
            # approximate vertical center of the line.
            line_y = (
                current_y
                + self.title_line_height
                * 0.5
            )

            self._render_text(
                line,
                text_x,
                line_y,
                scale=self.title_scale,
            )

            current_y += (
                self.title_line_height
            )

        # ------------------------------------------------------
        # Spacing
        # ------------------------------------------------------

        if (
            title_lines
            and description_lines
        ):
            current_y += (
                self.title_description_spacing
            )

        # ------------------------------------------------------
        # Description
        # ------------------------------------------------------

        for line in description_lines:
            line_y = (
                current_y
                + self.description_line_height
                * 0.5
            )

            self._render_text(
                line,
                text_x,
                line_y,
                scale=self.description_scale,
            )

            current_y += (
                self.description_line_height
            )