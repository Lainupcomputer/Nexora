from __future__ import annotations


class DebugConsoleRenderer:
    """Renderer-only view for the global engine console."""

    def __init__(self) -> None:
        self.height_ratio = 0.52
        self.margin = 18.0
        self.text_scale = 1.12
        self.line_spacing = 5.0
        self.layer_base = 2_000_000

    def render(self, renderer, console) -> None:
        if not console.is_open:
            return

        width = float(renderer.width)
        height = float(renderer.height)
        half_width = width * 0.5
        half_height = height * 0.5
        panel_height = max(180.0, height * self.height_ratio)

        panel_left = -half_width
        panel_top = -half_height

        # Background and input strip. Rect coordinates are centered by
        # default, therefore origin=(0, 0) keeps layout top-left based.
        renderer.rect(
            panel_left,
            panel_top,
            width,
            panel_height,
            origin=(0.0, 0.0),
            color=(0.025, 0.028, 0.035, 0.68),
            layer=self.layer_base,
        )

        _, measured_height = renderer.text_measure(
            "Ag",
            scale=self.text_scale,
        )
        line_height = measured_height + self.line_spacing
        baseline = renderer.text_baseline(scale=self.text_scale)
        input_height = line_height + 20.0
        input_top = panel_top + panel_height - input_height

        renderer.rect(
            panel_left,
            input_top,
            width,
            input_height,
            origin=(0.0, 0.0),
            color=(0.055, 0.06, 0.075, 0.82),
            layer=self.layer_base + 1,
        )

        title = "Nexora Debug Console"
        renderer.text(
            title,
            panel_left + self.margin,
            panel_top + self.margin + baseline,
            scale=self.text_scale,
            layer=self.layer_base + 2,
        )

        output_top = panel_top + self.margin + line_height + 6.0
        output_bottom = input_top - 6.0
        visible_count = max(
            1,
            int((output_bottom - output_top) // line_height),
        )

        lines = console.visible_lines(visible_count)
        y = output_top + baseline

        for line in lines:
            renderer.text(
                line.display_text,
                panel_left + self.margin,
                y,
                scale=self.text_scale,
                alpha=line.alpha,
                layer=self.layer_base + 2,
            )
            y += line_height

        prompt = "> " + console.input_text
        if console.cursor_visible:
            prompt += "_"

        renderer.text(
            prompt,
            panel_left + self.margin,
            input_top + 10.0 + baseline,
            scale=self.text_scale,
            layer=self.layer_base + 3,
        )
