from __future__ import annotations

from nexora.editor.ui import Rect, draw_rect, draw_text, rgba


class CutsceneTimelineMixin:

    def _timeline_time_from_x(self, x: float) -> float:
        width = max(1.0, self.timeline.width - self.timeline_label_width - 18.0)
        return max(0.0, min(self.asset.duration, (x - self.timeline.x - self.timeline_label_width) / width * self.asset.duration))

    def _timeline_x(self, time: float) -> float:
        width = max(1.0, self.timeline.width - self.timeline_label_width - 18.0)
        return self.timeline.x + self.timeline_label_width + max(0.0, min(self.asset.duration, time)) / max(self.asset.duration, 0.1) * width

    def _update_timeline(self, input_manager, mouse_x: float, mouse_y: float) -> None:
        if not self.timeline.contains(mouse_x, mouse_y) or not input_manager.mouse_pressed("left"):
            return
        if mouse_y < self.timeline.y + self.timeline_header_height:
            return
        was_playing = self.player.playing
        self.current_time = self._timeline_time_from_x(mouse_x)
        self.player.seek(self.current_time)
        self._stop_editor_audio()
        self._audio_last_time = self.current_time
        self._audio_paused = False
        if was_playing:
            self._preload_audio_tracks()
            self._start_audio_at_playhead()
        row = int((mouse_y - self.timeline.y - self.timeline_header_height) // 38.0)
        if 0 <= row < len(self.asset.tracks):
            track = self.asset.tracks[row]
            self.selected_track = row
            self.track_list.selected = row
            closest = None
            distance = 10.0
            for index, frame in enumerate(track.keyframes):
                difference = abs(self._timeline_x(frame.time) - mouse_x)
                if difference < distance:
                    closest = index
                    distance = difference
            self.selected_keyframe = (row, closest) if closest is not None else None
            self._refresh_track_controls()
            self._refresh_key_controls()
        self._refresh_preview_texture()

    def _render_timeline(self, renderer, viewport_size: tuple[float, float]) -> None:
        self.play_button.render(renderer, viewport_size, self.theme)
        self.pause_button.render(renderer, viewport_size, self.theme)
        self.stop_button.render(renderer, viewport_size, self.theme)
        self.add_keyframe_button.render(renderer, viewport_size, self.theme)
        self.delete_keyframe_button.render(renderer, viewport_size, self.theme)
        self.insert_image_button.render(renderer, viewport_size, self.theme)
        self.camera_keyframe_button.render(renderer, viewport_size, self.theme)
        timeline_x = self.timeline.x + self.timeline_label_width
        timeline_width = self.timeline.width - self.timeline_label_width - 18.0
        draw_text(renderer, "Timeline", self.timeline.x + 12.0, self.timeline.y + 14.0, viewport_size, scale=0.74)
        draw_text(renderer, f"{self.current_time:.2f}s", self.timeline.x + self.timeline_label_width - 12.0, self.timeline.y + 16.0, viewport_size, scale=0.52, color=self.theme.accent, align="right")
        steps = max(1, int(self.asset.duration))
        interval = 1.0 if self.asset.duration <= 20.0 else 5.0
        tick = 0.0
        while tick <= self.asset.duration + 0.001:
            x = timeline_x + tick / max(self.asset.duration, 0.1) * timeline_width
            renderer.line(*self._renderer_point(x, self.timeline.y + self.timeline_header_height), *self._renderer_point(x, self.timeline.y + self.timeline.height - 10.0), width=1.0, color=rgba((54, 61, 73, 180)))
            draw_text(renderer, f"{tick:.0f}s", x + 3.0, self.timeline.y + 22.0, viewport_size, scale=0.42, color=self.theme.muted)
            tick += interval
        del steps
        for row, track in enumerate(self.asset.tracks):
            y = self.timeline.y + self.timeline_header_height + row * 38.0
            draw_text(renderer, track.name, self.timeline.x + 12.0, y + 9.0, viewport_size, scale=0.52, color=self.theme.text if row == self.selected_track else self.theme.muted)
            renderer.line(*self._renderer_point(timeline_x, y + 19.0), *self._renderer_point(self.timeline.x + self.timeline.width - 10.0, y + 19.0), width=1.0, color=rgba(self.theme.border))
            for index, frame in enumerate(track.keyframes):
                x = self._timeline_x(frame.time)
                selected = self.selected_keyframe == (row, index)
                draw_rect(renderer, Rect(x - 6.0, y + 13.0, 12.0, 12.0), self.theme.accent if selected else self.theme.warning, viewport_size, radius=2.0)
        playhead_x = self._timeline_x(self.current_time)
        renderer.line(*self._renderer_point(playhead_x, self.timeline.y + self.timeline_header_height), *self._renderer_point(playhead_x, self.timeline.y + self.timeline.height - 8.0), width=2.0, color=rgba(self.theme.accent))
