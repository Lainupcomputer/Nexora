from __future__ import annotations

from copy import deepcopy

from nexora.gameplay.cutscene import CutsceneKeyframe, CutsceneTrack

from .cutscene_common import parse_float as _float


class CutsceneCameraMixin:

    def _camera_track(self) -> CutsceneTrack | None:
        return next(
            (track for track in self.asset.tracks if track.enabled and track.track_type == "camera"),
            None,
        )

    def _edit_camera_keyframe(self) -> None:
        """Select/create the camera keyframe at the current playhead."""

        track = self._camera_track()
        if track is None:
            track = CutsceneTrack("Camera", "camera")
            self.asset.add_track(track)
        value = self.player.evaluate_track(track, self.current_time)
        if not isinstance(value, dict):
            value = {"x": 0.0, "y": 0.0, "zoom": 1.0}
        self._set_camera_value_at_current(value)
        self.status = "Camera selected: edit X/Y/Zoom or drag with MMB"

    def _set_camera_value_at_current(self, value: dict) -> None:
        track = self._camera_track()
        if track is None:
            track = CutsceneTrack("Camera", "camera")
            self.asset.add_track(track)
        frame = next(
            (item for item in track.keyframes if abs(item.time - self.current_time) < 0.0005),
            None,
        )
        if frame is None:
            frame = CutsceneKeyframe(self.current_time, value, interpolation="ease_in_out")
            track.add_keyframe(frame)
        else:
            frame.value = deepcopy(value)
        self.selected_track = self.asset.tracks.index(track)
        self.selected_keyframe = (self.selected_track, track.keyframes.index(frame))
        self.dirty = True
        self._refresh_track_list()
        self._refresh_track_controls()
        self._refresh_key_controls()

    def _update_camera_viewport(self, input_manager, mouse_x: float, mouse_y: float) -> None:
        if self.modal is not None or not self.viewport.contains(mouse_x, mouse_y):
            return
        track = self._camera_track()
        if track is None:
            return
        value = self.player.evaluate_track(track, self.current_time)
        value = dict(value) if isinstance(value, dict) else {"x": 0.0, "y": 0.0, "zoom": 1.0}
        changed = False
        _wheel_x, wheel_y = input_manager.wheel
        if wheel_y:
            value["zoom"] = max(0.05, min(8.0, _float(value.get("zoom", 1.0), 1.0) * (1.15 ** float(wheel_y))))
            changed = True
        if input_manager.mouse_down("middle"):
            delta_x, delta_y = input_manager.mouse_delta
            preview_width = min(self.viewport.width - 60.0, 720.0)
            world_scale = max(preview_width, 1.0) / 640.0
            zoom = max(0.05, _float(value.get("zoom", 1.0), 1.0))
            value["x"] = _float(value.get("x", 0.0)) - delta_x / world_scale / zoom
            value["y"] = _float(value.get("y", 0.0)) - delta_y / world_scale / zoom
            changed = bool(delta_x or delta_y)
        if changed:
            self._set_camera_value_at_current(value)
            self.status = "Camera keyframe edited"
