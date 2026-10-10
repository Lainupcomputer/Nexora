from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from nexora.gameplay.cutscene import CutsceneAsset, CutsceneKeyframe, CutscenePlayer, CutsceneTrack, INTERPOLATIONS, TRACK_TYPES

from .cutscene_common import parse_float as _float


class CutsceneDocumentMixin:

    def _set_asset(self, asset: CutsceneAsset) -> None:
        self._stop_editor_audio()
        self.asset = asset
        self.player = CutscenePlayer(asset, on_event=self._event_fired)
        self.document_field.set_text(asset.name)
        self.duration_field.set_text(f"{asset.duration:.3f}")
        self.fps_field.set_text(f"{asset.fps:.3f}")
        self.current_time = 0.0
        self.selected_track = 0
        self.selected_keyframe = None
        self.preview_reference = ""
        self.preview_texture = None
        self.preview_error = ""
        self._audio_last_time = 0.0
        self._audio_paused = False
        self._refresh_track_controls()
        self._refresh_key_controls()
        self._refresh_track_list()

    def new_cutscene(self) -> None:
        asset = CutsceneAsset(name="Untitled Cutscene", duration=10.0, fps=60.0)
        image = CutsceneTrack("Image", "image")
        image.add_keyframe(CutsceneKeyframe(0.0, {"path": ""}))
        camera = CutsceneTrack("Camera", "camera")
        camera.add_keyframe(CutsceneKeyframe(0.0, {"x": 0.0, "y": 0.0, "zoom": 1.0}))
        fade = CutsceneTrack("Fade", "fade")
        fade.add_keyframe(CutsceneKeyframe(0.0, {"alpha": 0.0, "color": [0.0, 0.0, 0.0]}))
        asset.tracks = [image, camera, fade]
        self._set_asset(asset)
        self.document_path = None
        self.document_name = "Untitled"
        self.dirty = False
        self.status = "New Cutscene"

    def _load_asset(self, path: Path) -> None:
        try:
            asset = CutsceneAsset.load(path, signing_key=self._signing_key())
            self._set_asset(asset)
            self.document_path = path.resolve()
            self.document_name = path.stem
            self.dirty = False
            self.status = f"Opened {path.name}"
            self._preload_audio_tracks()
        except Exception as exc:
            self.status = f"Could not open Cutscene: {exc}"

    def save_cutscene(self) -> None:
        if self.document_path is None:
            self._open_browser("save")
            return
        self._save_asset(self.document_path)

    def _save_asset(self, path: Path) -> None:
        try:
            self._apply_document_fields()
            saved = self.asset.save(path, signing_key=self._signing_key())
            self.document_path = saved
            self.document_name = saved.stem
            self.dirty = False
            self.status = f"Saved {saved.name}"
        except Exception as exc:
            self.status = f"Could not save Cutscene: {exc}"

    def _refresh_track_list(self) -> None:
        labels = [
            f"{track.name}  [{track.track_type.title()}]"
            for track in self.asset.tracks
        ]
        self.track_list.set_items(labels)
        if labels:
            self.selected_track = max(0, min(self.selected_track, len(labels) - 1))
            self.track_list.selected = self.selected_track

    def _track_selected(self, index: int) -> None:
        if 0 <= index < len(self.asset.tracks):
            self.selected_track = index
            self.selected_keyframe = None
            self._refresh_track_controls()
            self._refresh_key_controls()

    def _active_track(self) -> CutsceneTrack | None:
        if 0 <= self.selected_track < len(self.asset.tracks):
            return self.asset.tracks[self.selected_track]
        return None

    def _selected_frame(self) -> CutsceneKeyframe | None:
        track = self._active_track()
        if track is None or self.selected_keyframe is None:
            return None
        track_index, frame_index = self.selected_keyframe
        if track_index != self.selected_track or not 0 <= frame_index < len(track.keyframes):
            return None
        return track.keyframes[frame_index]

    def _refresh_track_controls(self) -> None:
        track = self._active_track()
        if track is None:
            return
        self.track_name_field.set_text(track.name)
        self.track_type.selected = TRACK_TYPES.index(track.track_type)
        self.track_enabled.checked = track.enabled

    def _refresh_key_controls(self) -> None:
        frame = self._selected_frame()
        value = frame.value if frame is not None and isinstance(frame.value, dict) else {}
        self.key_time_field.set_text(f"{frame.time:.3f}" if frame else "0.0")
        track = self._active_track()
        track_type = track.track_type if track else "image"
        if track_type in {"image", "audio"}:
            self.key_value_field.set_text(str(value.get("path", "")))
        elif track_type == "event":
            self.key_value_field.set_text(str(value.get("id", "")))
        elif track_type == "effect":
            self.key_value_field.set_text(str(value.get("name", "")))
        else:
            self.key_value_field.set_text(str(value.get("value", "")))
        self.key_x_field.set_text(f"{_float(value.get('x', 0.0)):.3f}")
        self.key_y_field.set_text(f"{_float(value.get('y', 0.0)):.3f}")
        self.key_zoom_field.set_text(f"{_float(value.get('zoom', 1.0), 1.0):.3f}")
        self.key_alpha_field.set_text(f"{_float(value.get('alpha', 0.0)):.3f}")
        self.key_volume_field.set_text(f"{_float(value.get('volume', 1.0), 1.0):.3f}")
        self.key_value_field.visible = track_type in {"image", "audio", "event", "effect"}
        self.key_browse_button.visible = track_type in {"image", "audio"}
        self.key_x_field.visible = track_type == "camera"
        self.key_y_field.visible = track_type == "camera"
        self.key_zoom_field.visible = track_type == "camera"
        self.key_alpha_field.visible = track_type in {"fade", "effect"}
        self.key_volume_field.visible = track_type == "audio"
        if frame is not None:
            self.key_interpolation.selected = max(0, INTERPOLATIONS.index(frame.interpolation))
        else:
            self.key_interpolation.selected = 0

    def _properties_changed(self, _value: str) -> None:
        self._apply_document_fields()
        self._apply_selected_properties()

    def _apply_document_fields(self) -> None:
        self.asset.name = self.document_field.text.strip() or "Untitled Cutscene"
        self.document_name = self.asset.name
        self.asset.duration = max(0.1, _float(self.duration_field.text, self.asset.duration))
        self.asset.fps = max(1.0, _float(self.fps_field.text, self.asset.fps))
        self.dirty = True

    def _apply_selected_properties(self) -> None:
        track = self._active_track()
        frame = self._selected_frame()
        if track is None:
            return
        old_name = track.name
        track.name = self.track_name_field.text.strip() or old_name
        track.enabled = self.track_enabled.checked
        frame = self._selected_frame()
        if frame is None:
            self._refresh_track_list()
            return
        frame.time = max(0.0, _float(self.key_time_field.text, frame.time))
        frame.interpolation = self.key_interpolation.value.lower() or "step"
        value = frame.value if isinstance(frame.value, dict) else {}
        track_type = track.track_type
        if track_type in {"image", "audio"}:
            previous_value = dict(value)
            value = {"path": self.key_value_field.text.strip()}
            if track_type == "audio":
                value["volume"] = max(0.0, _float(self.key_volume_field.text, 1.0))
                for key in ("channel", "bus", "loop", "stream", "fade_in", "fade_out", "optional", "action", "duration"):
                    if key in previous_value:
                        value[key] = previous_value[key]
        elif track_type == "event":
            value = {"id": self.key_value_field.text.strip(), "parameters": {}}
        elif track_type == "effect":
            value = {"name": self.key_value_field.text.strip(), "intensity": max(0.0, _float(self.key_alpha_field.text, 1.0))}
        elif track_type == "camera":
            value = {
                "x": _float(self.key_x_field.text),
                "y": _float(self.key_y_field.text),
                "zoom": max(0.01, _float(self.key_zoom_field.text, 1.0)),
            }
        elif track_type == "fade":
            value = {"alpha": max(0.0, min(1.0, _float(self.key_alpha_field.text))), "color": [0.0, 0.0, 0.0]}
        frame.value = value
        track.sort_keyframes()
        self.selected_keyframe = (self.selected_track, track.keyframes.index(frame))
        self.current_time = min(self.current_time, self.asset.duration)
        self.dirty = True
        self._refresh_track_list()
        self._refresh_preview_texture()

    def _track_type_changed(self, _index: int, value: str) -> None:
        track = self._active_track()
        if track is None:
            return
        track.track_type = value.lower()
        if track.track_type not in TRACK_TYPES:
            track.track_type = "image"
        self.selected_keyframe = None
        self.dirty = True
        self._refresh_track_list()
        self._refresh_key_controls()

    def _track_enabled_changed(self, value: bool) -> None:
        track = self._active_track()
        if track is not None:
            track.enabled = bool(value)
            self.dirty = True

    def _key_interpolation_changed(self, _index: int, value: str) -> None:
        frame = self._selected_frame()
        if frame is not None:
            frame.interpolation = value.lower()
            self.dirty = True

    def _add_track(self) -> None:
        base = "Track"
        names = {track.name for track in self.asset.tracks}
        index = 1
        name = base
        while name in names:
            index += 1
            name = f"{base} {index}"
        track = CutsceneTrack(name, "effect")
        track.add_keyframe(CutsceneKeyframe(self.current_time, {"name": "", "intensity": 1.0}))
        self.asset.add_track(track)
        self.selected_track = len(self.asset.tracks) - 1
        self.selected_keyframe = (self.selected_track, 0)
        self.dirty = True
        self._refresh_track_list()
        self._refresh_track_controls()
        self._refresh_key_controls()
        self.status = f"Added {name}"

    def _remove_track(self) -> None:
        if not self.asset.tracks:
            return
        removed = self.asset.tracks.pop(self.selected_track)
        self.selected_track = max(0, min(self.selected_track, len(self.asset.tracks) - 1))
        self.selected_keyframe = None
        self.dirty = True
        self._refresh_track_list()
        self._refresh_track_controls()
        self._refresh_key_controls()
        self.status = f"Removed {removed.name}"

    def _add_keyframe(self) -> None:
        track = self._active_track()
        if track is None:
            self._add_track()
            track = self._active_track()
        if track is None:
            return
        value = self.player.evaluate_track(track, self.current_time)
        if value is None:
            defaults = {
                "image": {"path": ""},
                "camera": {"x": 0.0, "y": 0.0, "zoom": 1.0},
                "fade": {"alpha": 0.0, "color": [0.0, 0.0, 0.0]},
                "audio": {"path": "", "volume": 1.0},
                "effect": {"name": "", "intensity": 1.0},
                "event": {"id": "", "parameters": {}},
            }
            value = defaults[track.track_type]
        frame = CutsceneKeyframe(self.current_time, deepcopy(value))
        track.add_keyframe(frame)
        self.selected_keyframe = (self.selected_track, track.keyframes.index(frame))
        self.dirty = True
        self._refresh_key_controls()
        self.status = f"Added keyframe at {self.current_time:.2f}s"

    def _insert_image_keyframe(self) -> None:
        self._insert_asset_keyframe("image")

    def _insert_audio_keyframe(self) -> None:
        self._insert_asset_keyframe("audio")

    def _insert_asset_keyframe(self, track_type: str) -> None:
        track_index = next(
            (index for index, track in enumerate(self.asset.tracks) if track.track_type == track_type),
            None,
        )
        if track_index is None:
            track = CutsceneTrack(track_type.title(), track_type)
            defaults = {
                "image": {"path": ""},
                "audio": {"path": "", "volume": 1.0},
            }
            track.add_keyframe(CutsceneKeyframe(self.current_time, defaults[track_type]))
            self.asset.add_track(track)
            track_index = len(self.asset.tracks) - 1
        else:
            track = self.asset.tracks[track_index]
            value = self.player.evaluate_track(track, self.current_time)
            if not isinstance(value, dict):
                value = {"path": ""}
                if track_type == "audio":
                    value["volume"] = 1.0
            frame = CutsceneKeyframe(self.current_time, deepcopy(value))
            track.add_keyframe(frame)

        self.selected_track = track_index
        track = self.asset.tracks[track_index]
        self.selected_keyframe = (
            track_index,
            min(
                range(len(track.keyframes)),
                key=lambda index: abs(track.keyframes[index].time - self.current_time),
            ),
        )
        self.dirty = True
        self._refresh_track_list()
        self._refresh_track_controls()
        self._refresh_key_controls()
        self._open_browser(track_type)
        self.status = f"Choose {track_type} asset"

    def _delete_keyframe(self) -> None:
        frame = self._selected_frame()
        track = self._active_track()
        if frame is None or track is None:
            self.status = "Select a keyframe first."
            return
        track.keyframes.remove(frame)
        self.selected_keyframe = None
        self.dirty = True
        self._refresh_key_controls()
        self.status = "Keyframe deleted"
