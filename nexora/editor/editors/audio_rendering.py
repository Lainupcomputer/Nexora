from __future__ import annotations

"""Layout and rendering for the standalone audio mixer editor."""

import math

from nexora.editor.ui import (
    Control,
    Rect,
    draw_outline,
    draw_rect,
    draw_text,
    render_document_title,
    render_editor_shell,
    render_status_bar,
)


def _dbfs_label(value: float) -> str:
    if not math.isfinite(value):
        return "-inf"
    return f"{value:.1f} dB"


class AudioRenderingMixin:
    def _layout(self) -> tuple[float, float]:
        width = float(self.game.window.width)
        height = float(self.game.window.height)
        if (width, height) == self._layout_size:
            return width, height
        self._layout_size = (width, height)

        left = 10.0
        top = self.TOOLBAR_HEIGHT + 10.0
        bottom = height - self.STATUS_HEIGHT - 10.0
        left_panel_w = self.LEFT_WIDTH
        right_x = width - self.RIGHT_WIDTH - 10.0
        center_x = left + left_panel_w + 10.0
        center_w = max(360.0, right_x - center_x - 10.0)

        self.bus_list.rect = Rect(left, top + 34.0, left_panel_w, max(180.0, bottom - top - 126.0))
        self.add_bus_name.rect = Rect(left, bottom - 78.0, left_panel_w - 92.0, 32.0)
        self.add_bus_button.rect = Rect(left + left_panel_w - 84.0, bottom - 78.0, 84.0, 32.0)
        self.remove_bus_button.rect = Rect(left, bottom - 38.0, left_panel_w, 32.0)

        cx = center_x + 14.0
        field_w = min(360.0, center_w - 28.0)
        self.rename_field.rect = Rect(cx, top + 42.0, field_w - 92.0, 32.0)
        self.rename_button.rect = Rect(cx + field_w - 84.0, top + 42.0, 84.0, 32.0)
        self.parent_dropdown.rect = Rect(cx, top + 104.0, field_w, 32.0)
        self.volume_slider.rect = Rect(cx, top + 176.0, field_w, 24.0)
        self.pan_slider.rect = Rect(cx, top + 238.0, field_w, 24.0)
        self.mute_check.rect = Rect(cx, top + 280.0, 90.0, 28.0)
        self.solo_check.rect = Rect(cx + 100.0, top + 280.0, 90.0, 28.0)
        self.bypass_chain_check.rect = Rect(cx + 200.0, top + 280.0, 180.0, 28.0)
        self.clear_peak_button.rect = Rect(cx, top + 394.0, 120.0, 30.0)
        for index, field in enumerate(self.effect_parameter_fields):
            column = index % 2
            row = index // 2
            field.rect = Rect(cx + column * 188.0, top + 484.0 + row * 58.0, 174.0, 32.0)

        rx = right_x + 12.0
        rw = self.RIGHT_WIDTH - 24.0
        self.preset_dropdown.rect = Rect(rx, top + 36.0, rw - 128.0, 32.0)
        self.apply_preset_button.rect = Rect(rx + rw - 120.0, top + 36.0, 120.0, 32.0)
        self.append_preset_check.rect = Rect(rx, top + 74.0, 110.0, 26.0)

        self.effect_list.rect = Rect(rx, top + 130.0, rw, 160.0)
        self.add_effect_dropdown.rect = Rect(rx, top + 300.0, rw - 120.0, 32.0)
        self.add_effect_button.rect = Rect(rx + rw - 112.0, top + 300.0, 112.0, 32.0)
        self.remove_effect_button.rect = Rect(rx, top + 338.0, 136.0, 30.0)
        self.effect_bypass_check.rect = Rect(rx + 148.0, top + 340.0, 160.0, 28.0)
        self.effect_wet_slider.rect = Rect(rx, top + 398.0, rw, 22.0)

        self.send_list.rect = Rect(rx, top + 466.0, rw, 122.0)
        self.send_target_dropdown.rect = Rect(rx, top + 598.0, rw - 110.0, 32.0)
        self.add_send_button.rect = Rect(rx + rw - 102.0, top + 598.0, 102.0, 32.0)
        self.send_amount_slider.rect = Rect(rx, top + 652.0, rw, 22.0)
        self.send_pre_check.rect = Rect(rx, top + 684.0, 126.0, 28.0)
        self.send_enabled_check.rect = Rect(rx + 132.0, top + 684.0, 110.0, 28.0)
        self.remove_send_button.rect = Rect(rx + rw - 122.0, top + 682.0, 122.0, 30.0)

        self.save_button.rect = Rect(105.0, 8.0, 118.0, 32.0)
        self.load_button.rect = Rect(231.0, 8.0, 118.0, 32.0)
        self.reset_button.rect = Rect(357.0, 8.0, 92.0, 32.0)
        return width, height

    def _controls(self) -> list[Control]:
        return [
            self.bus_list,
            self.add_bus_name,
            self.add_bus_button,
            self.remove_bus_button,
            self.rename_field,
            self.rename_button,
            self.parent_dropdown,
            self.volume_slider,
            self.pan_slider,
            self.mute_check,
            self.solo_check,
            self.bypass_chain_check,
            self.clear_peak_button,
            self.preset_dropdown,
            self.apply_preset_button,
            self.append_preset_check,
            self.effect_list,
            self.add_effect_dropdown,
            self.add_effect_button,
            self.remove_effect_button,
            self.effect_bypass_check,
            self.effect_wet_slider,
            *self.effect_parameter_fields,
            self.send_list,
            self.send_target_dropdown,
            self.add_send_button,
            self.send_amount_slider,
            self.send_pre_check,
            self.send_enabled_check,
            self.remove_send_button,
            self.save_button,
            self.load_button,
            self.reset_button,
        ]

    def _draw_meter(self, renderer, viewport: tuple[float, float], rect: Rect, value: float, peak: float, clipped: bool) -> None:
        draw_rect(renderer, rect, self.theme.input, viewport, radius=3.0)
        draw_outline(renderer, rect, self.theme.border, viewport)
        fraction = max(0.0, min(1.0, float(value)))
        fill = Rect(rect.x + 2.0, rect.y + 2.0, (rect.width - 4.0) * fraction, rect.height - 4.0)
        if fill.width > 0:
            draw_rect(renderer, fill, self.theme.error if clipped else self.theme.accent, viewport, radius=2.0)
        hold_x = rect.x + 2.0 + (rect.width - 4.0) * max(0.0, min(1.0, peak))
        draw_rect(renderer, Rect(hold_x, rect.y + 1.0, 2.0, rect.height - 2.0), self.theme.warning, viewport)

    def render(self, interpolation: float) -> None:
        del interpolation
        width, height = self._layout()
        viewport = (width, height)
        renderer = self.game.renderer
        draw_rect(renderer, Rect(0, 0, width, height), self.theme.background, viewport)
        with renderer.overlay_scope():
            body_height = height - self.TOOLBAR_HEIGHT - self.STATUS_HEIGHT - 20.0
            left_panel = Rect(10.0, self.TOOLBAR_HEIGHT + 10.0, self.LEFT_WIDTH, body_height)
            right_panel = Rect(width - self.RIGHT_WIDTH - 10.0, self.TOOLBAR_HEIGHT + 10.0, self.RIGHT_WIDTH, body_height)
            center_panel = Rect(
                left_panel.x + left_panel.width + 8.0,
                self.TOOLBAR_HEIGHT + 10.0,
                max(0.0, right_panel.x - (left_panel.x + left_panel.width) - 16.0),
                body_height,
            )
            render_editor_shell(
                renderer,
                viewport,
                self.theme,
                toolbar_height=self.TOOLBAR_HEIGHT,
                status_height=self.STATUS_HEIGHT,
                panels=(
                    (left_panel, self.theme.panel),
                    (center_panel, self.theme.viewport),
                    (right_panel, self.theme.panel),
                ),
                outline_rects=(left_panel, center_panel, right_panel),
            )
            render_document_title(
                renderer,
                viewport,
                self.theme,
                "Audio Mixer",
                x_offset=16.0,
                y=14.0,
                scale=0.62,
            )

            for button in (self.save_button, self.load_button, self.reset_button):
                button.render(renderer, viewport, self.theme)
            draw_text(renderer, "Buses", 20.0, self.TOOLBAR_HEIGHT + 18.0, viewport, scale=0.72)
            self.bus_list.render(renderer, viewport, self.theme)
            self.add_bus_name.render(renderer, viewport, self.theme)
            self.add_bus_button.render(renderer, viewport, self.theme)
            self.remove_bus_button.render(renderer, viewport, self.theme)

            bus = self._selected_bus()
            center_x = self.LEFT_WIDTH + 34.0
            if bus is not None:
                draw_text(renderer, bus.name, center_x, self.TOOLBAR_HEIGHT + 22.0, viewport, scale=0.92)
                draw_text(renderer, f"ID {bus.id[:12]}", center_x, self.TOOLBAR_HEIGHT + 58.0, viewport, scale=0.46, color=self.theme.muted)
                draw_text(renderer, "Parent", center_x, self.TOOLBAR_HEIGHT + 94.0, viewport, scale=0.48, color=self.theme.muted)
                draw_text(renderer, f"Volume  {bus.volume:.2f}", center_x, self.TOOLBAR_HEIGHT + 158.0, viewport, scale=0.50)
                draw_text(renderer, f"Pan  {bus.pan:+.2f}", center_x, self.TOOLBAR_HEIGHT + 220.0, viewport, scale=0.50)
                self.rename_field.render(renderer, viewport, self.theme)
                self.rename_button.render(renderer, viewport, self.theme)
                self.parent_dropdown.render(renderer, viewport, self.theme)
                self.volume_slider.render(renderer, viewport, self.theme)
                self.pan_slider.render(renderer, viewport, self.theme)
                self.mute_check.render(renderer, viewport, self.theme)
                self.solo_check.render(renderer, viewport, self.theme)
                self.bypass_chain_check.render(renderer, viewport, self.theme)

                peak_l, peak_r = bus.peak
                hold_l, hold_r = bus.peak_hold
                peak_db_l, peak_db_r = bus.peak_dbfs
                meter_y = self.TOOLBAR_HEIGHT + 335.0
                draw_text(renderer, "Meter L", center_x, meter_y - 20.0, viewport, scale=0.46, color=self.theme.muted)
                self._draw_meter(renderer, viewport, Rect(center_x, meter_y, 300.0, 18.0), peak_l, hold_l, bus.clipped)
                draw_text(renderer, _dbfs_label(peak_db_l), center_x + 310.0, meter_y - 1.0, viewport, scale=0.42, color=self.theme.muted)
                draw_text(renderer, "Meter R", center_x, meter_y + 26.0, viewport, scale=0.46, color=self.theme.muted)
                self._draw_meter(renderer, viewport, Rect(center_x, meter_y + 46.0, 300.0, 18.0), peak_r, hold_r, bus.clipped)
                draw_text(renderer, _dbfs_label(peak_db_r), center_x + 310.0, meter_y + 45.0, viewport, scale=0.42, color=self.theme.muted)
                self.clear_peak_button.render(renderer, viewport, self.theme)
                if self._effect_parameter_names:
                    draw_text(renderer, "Selected effect parameters", center_x, self.TOOLBAR_HEIGHT + 454.0, viewport, scale=0.54)
                    for index, parameter in enumerate(self._effect_parameter_names):
                        field = self.effect_parameter_fields[index]
                        draw_text(renderer, parameter, field.rect.x, field.rect.y - 18.0, viewport, scale=0.42, color=self.theme.muted)
                        field.render(renderer, viewport, self.theme)

            right_x = width - self.RIGHT_WIDTH
            draw_text(renderer, "Preset", right_x + 14.0, self.TOOLBAR_HEIGHT + 18.0, viewport, scale=0.62)
            self.preset_dropdown.render(renderer, viewport, self.theme)
            self.apply_preset_button.render(renderer, viewport, self.theme)
            self.append_preset_check.render(renderer, viewport, self.theme)
            draw_text(renderer, "DSP Effects", right_x + 14.0, self.TOOLBAR_HEIGHT + 112.0, viewport, scale=0.62)
            self.effect_list.render(renderer, viewport, self.theme)
            self.add_effect_dropdown.render(renderer, viewport, self.theme)
            self.add_effect_button.render(renderer, viewport, self.theme)
            self.remove_effect_button.render(renderer, viewport, self.theme)
            self.effect_bypass_check.render(renderer, viewport, self.theme)
            draw_text(renderer, f"Wet {self.effect_wet_slider.value:.0%}", right_x + 14.0, self.TOOLBAR_HEIGHT + 382.0, viewport, scale=0.46, color=self.theme.muted)
            self.effect_wet_slider.render(renderer, viewport, self.theme)

            draw_text(renderer, "Sends", right_x + 14.0, self.TOOLBAR_HEIGHT + 446.0, viewport, scale=0.62)
            self.send_list.render(renderer, viewport, self.theme)
            self.send_target_dropdown.render(renderer, viewport, self.theme)
            self.add_send_button.render(renderer, viewport, self.theme)
            draw_text(renderer, f"Amount {self.send_amount_slider.value:.2f}", right_x + 14.0, self.TOOLBAR_HEIGHT + 636.0, viewport, scale=0.46, color=self.theme.muted)
            self.send_amount_slider.render(renderer, viewport, self.theme)
            self.send_pre_check.render(renderer, viewport, self.theme)
            self.send_enabled_check.render(renderer, viewport, self.theme)
            self.remove_send_button.render(renderer, viewport, self.theme)

            render_status_bar(
                renderer,
                viewport,
                self.theme,
                self.status,
                "Nexora Audio Editor",
                status_height=self.STATUS_HEIGHT,
                scale=0.50,
            )
