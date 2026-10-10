from __future__ import annotations


class CutscenePlaybackMixin:

    def _play(self) -> None:
        if self.player.finished:
            self.player.seek(0.0)
            self._stop_editor_audio()
            self._audio_last_time = 0.0
        if self._audio_paused:
            if self._audio_sources:
                self._resume_editor_audio()
            else:
                self._preload_audio_tracks()
                self._start_audio_at_playhead()
            self._audio_paused = False
        else:
            self._stop_editor_audio()
            self._preload_audio_tracks()
            self._start_audio_at_playhead()
        self.player.play()
        self.status = "Playing"

    def _pause(self) -> None:
        self.player.pause()
        self._pause_editor_audio()
        self._audio_paused = True
        self.status = "Paused"

    def _stop(self) -> None:
        self.player.stop()
        self._stop_editor_audio()
        self._audio_last_time = 0.0
        self._audio_paused = False
        self.current_time = 0.0
        self.status = "Stopped"

    def _toggle_playback(self) -> None:
        self._pause() if self.player.playing else self._play()

    def _reset_preview(self) -> None:
        self.preview_texture = None
        self.preview_reference = ""
        self.preview_error = ""
        self._refresh_preview_texture()

    def _event_fired(self, event_id: str, _parameters: dict) -> None:
        self.status = f"Event: {event_id}"

    def _current_value(self, track_type: str) -> dict:
        for track in self.asset.tracks:
            if track.track_type == track_type and track.enabled:
                value = self.player.evaluate_track(track, self.current_time)
                if isinstance(value, dict):
                    return value
        return {}

    def _refresh_preview_texture(self) -> None:
        value = self._current_value("image")
        reference = str(value.get("path", "")).strip()
        if not reference:
            self.preview_texture = None
            self.preview_reference = ""
            self.preview_error = ""
            return
        if reference == self.preview_reference and self.preview_texture is not None:
            return
        path = self._asset_path(reference)
        try:
            self.preview_texture = self.game.engine.assets.texture(path)
            self.preview_reference = reference
            self.preview_error = ""
        except Exception as exc:
            self.preview_texture = None
            self.preview_reference = reference
            self.preview_error = str(exc)
