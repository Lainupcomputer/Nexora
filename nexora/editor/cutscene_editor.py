from __future__ import annotations

"""Standalone timeline editor for Nexora ``.ncutscene`` assets."""

from copy import deepcopy
from pathlib import Path

from nexora import Game
from nexora.audio import AudioChannel, AudioSource
from nexora.cutscene import (
    CUTSCENE_ASSET_SUFFIX,
    CutsceneAsset,
    CutsceneKeyframe,
    CutscenePlayer,
    CutsceneTrack,
    INTERPOLATIONS,
    TRACK_TYPES,
)
from nexora.editor.app import resolve_project_path
from nexora.editor.model import EditorProjectContext
from nexora.editor.ui import (
    Button,
    CheckBox,
    Dropdown,
    ListBox,
    Menu,
    Rect,
    TextField,
    UITheme,
    FileBrowserModel,
    centered_rect,
    close_other_menus,
    draw_outline,
    draw_rect,
    draw_text,
    rgba,
    sync_browser_list,
)
from nexora.scene import Scene


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
AUDIO_EXTENSIONS = (".wav", ".ogg", ".mp3", ".flac")
DEFAULT_SIGNING_KEY = (
    b"nexora-default-save-signing-key-"
    b"change-this-for-your-game"
)


def _float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float(default)


class CutsceneEditorScene(Scene):
    """Renderer-backed cutscene editor with a timeline and live preview."""

    TOOLBAR_HEIGHT = 58.0
    STATUS_HEIGHT = 30.0
    LEFT_WIDTH = 250.0
    RIGHT_WIDTH = 350.0
    TIMELINE_HEIGHT = 290.0

    def __init__(
        self,
        game,
        project_path: Path,
        cutscene_path: str | Path | None = None,
        project_context: EditorProjectContext | None = None,
    ) -> None:
        super().__init__("StandaloneCutsceneEditor")
        self.game = game
        self.project_context = project_context or EditorProjectContext.from_path(project_path)
        self.project_path = self.project_context.root
        self.requested_cutscene_path = Path(cutscene_path).expanduser() if cutscene_path is not None else None
        self.assets_root = self._asset_root()
        self.theme = UITheme()

        self.asset = CutsceneAsset()
        self.player = CutscenePlayer(self.asset, on_event=self._event_fired)
        self.document_path: Path | None = None
        self.document_name = "Untitled"
        self.dirty = False
        self.status = "Ready"
        self.modal: str | None = None
        self.browser_mode = "open"
        self.browser_root = self.project_path
        self.browser_path = self.project_path
        self.browser_entries: list[Path] = []
        self.file_browser = FileBrowserModel()
        self.preview_texture = None
        self.preview_reference = ""
        self.preview_error = ""
        self._audio_cache: dict[str, object] = {}
        self._audio_sources: dict[str, list[AudioSource]] = {}
        self._audio_last_time = 0.0
        self._audio_paused = False

        self.viewport = Rect(0, 0, 1, 1)
        self.left_panel = Rect(0, 0, 1, 1)
        self.right_panel = Rect(0, 0, 1, 1)
        self.timeline = Rect(0, 0, 1, 1)
        self._layout_size = (-1.0, -1.0)

        self.selected_track = 0
        self.selected_keyframe: tuple[int, int] | None = None
        self.current_time = 0.0
        self.timeline_label_width = 250.0
        self.timeline_header_height = 42.0

        self.track_list = ListBox(Rect(0, 0, 1, 1), self._track_selected)
        self.track_list.row_height = 32.0
        self.add_track_button = Button(Rect(0, 0, 1, 1), "+ Track", self._add_track)
        self.remove_track_button = Button(Rect(0, 0, 1, 1), "- Track", self._remove_track)
        self.add_keyframe_button = Button(Rect(0, 0, 1, 1), "Add Keyframe", self._add_keyframe)
        self.delete_keyframe_button = Button(Rect(0, 0, 1, 1), "Delete Keyframe", self._delete_keyframe)
        self.insert_image_button = Button(Rect(0, 0, 1, 1), "Insert Image", self._insert_image_keyframe)
        self.play_button = Button(Rect(0, 0, 1, 1), "Play", self._play)
        self.pause_button = Button(Rect(0, 0, 1, 1), "Pause", self._pause)
        self.stop_button = Button(Rect(0, 0, 1, 1), "Stop", self._stop)

        self.document_field = TextField(Rect(0, 0, 1, 1), "Untitled Cutscene")
        self.duration_field = TextField(Rect(0, 0, 1, 1), "10.0")
        self.fps_field = TextField(Rect(0, 0, 1, 1), "60.0")
        self.track_name_field = TextField(Rect(0, 0, 1, 1), "Track")
        self.track_type = Dropdown(Rect(0, 0, 1, 1), tuple(item.title() for item in TRACK_TYPES), on_change=self._track_type_changed)
        self.track_enabled = CheckBox(Rect(0, 0, 1, 1), "Enabled", True, self._track_enabled_changed)

        self.key_time_field = TextField(Rect(0, 0, 1, 1), "0.0")
        self.key_value_field = TextField(Rect(0, 0, 1, 1), "", "Asset path / event id")
        self.key_x_field = TextField(Rect(0, 0, 1, 1), "0.0")
        self.key_y_field = TextField(Rect(0, 0, 1, 1), "0.0")
        self.key_zoom_field = TextField(Rect(0, 0, 1, 1), "1.0")
        self.key_alpha_field = TextField(Rect(0, 0, 1, 1), "0.0")
        self.key_volume_field = TextField(Rect(0, 0, 1, 1), "1.0")
        self.key_interpolation = Dropdown(Rect(0, 0, 1, 1), tuple(item.title() for item in INTERPOLATIONS), on_change=self._key_interpolation_changed)
        self.key_browse_button = Button(Rect(0, 0, 1, 1), "Browse", self._browse_key_asset)
        self.camera_keyframe_button = Button(Rect(0, 0, 1, 1), "Camera Keyframe", self._edit_camera_keyframe)

        for field in (
            self.document_field,
            self.duration_field,
            self.fps_field,
            self.track_name_field,
            self.key_time_field,
            self.key_value_field,
            self.key_x_field,
            self.key_y_field,
            self.key_zoom_field,
            self.key_alpha_field,
            self.key_volume_field,
        ):
            field.on_change = self._properties_changed

        self.browser_list = ListBox(Rect(0, 0, 1, 1), self._browser_selected)
        self.browser_name = TextField(Rect(0, 0, 1, 1), "", "File name")
        self.browser_cancel_button = Button(Rect(0, 0, 1, 1), "Cancel", self._close_modal)
        self.browser_action_button = Button(Rect(0, 0, 1, 1), "Save", self._browser_action)
        self.info_close_button = Button(Rect(0, 0, 1, 1), "Close", self._close_modal)

        self.file_menu = Menu(
            Rect(0, 0, 1, 1),
            "File",
            [
                ("New", self.new_cutscene),
                ("Open", lambda: self._open_browser("open")),
                ("Save", self.save_cutscene),
                ("Save As", lambda: self._open_browser("save")),
                ("Exit", self.game.stop),
            ],
        )
        self.cutscene_menu = Menu(
            Rect(0, 0, 1, 1),
            "Cutscene",
            [
                ("Add Track", self._add_track),
                ("Add Keyframe", self._add_keyframe),
                ("Insert Image Keyframe", self._insert_image_keyframe),
                ("Insert Audio Keyframe", self._insert_audio_keyframe),
                ("Edit Camera at Playhead", self._edit_camera_keyframe),
                ("Delete Keyframe", self._delete_keyframe),
                ("Play / Pause", self._toggle_playback),
            ],
        )
        self.view_menu = Menu(
            Rect(0, 0, 1, 1),
            "View",
            [("Reset Playhead", lambda: self.player.seek(0.0)), ("Reset Preview", self._reset_preview)],
        )
        self.help_menu = Menu(
            Rect(0, 0, 1, 1),
            "Help",
            [("Keyboard Shortcuts", self._show_help), ("About Cutscene Editor", self._show_about)],
        )
        self.menus = [self.file_menu, self.cutscene_menu, self.view_menu, self.help_menu]
        for menu in self.menus:
            menu.on_open = self._menu_opened

        self.new_cutscene()
        if cutscene_path is not None:
            self._load_asset(self._resolve_requested_path(cutscene_path))

    # ------------------------------------------------------------------
    # Asset and document paths
    # ------------------------------------------------------------------

    def _asset_root(self) -> Path:
        return self.project_context.asset_root_for(self.requested_cutscene_path)

    def _asset_relative(self, path: Path) -> str:
        return self.project_context.relative_asset(path, root=self.assets_root)

    def _resolve_asset_path(self, value: str | Path) -> Path:
        return self.project_context.resolve_asset(
            value,
            reference=self.requested_cutscene_path,
        )

    def _resolve_requested_path(self, value: str | Path) -> Path:
        return self.project_context.resolve_project_file(
            value,
            roots=(self.project_context.cutscenes_root,),
        )

    def _signing_key(self):
        return getattr(self.game, "_scene_signing_key", DEFAULT_SIGNING_KEY)

    # ------------------------------------------------------------------
    # Document state
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Track and keyframe editing
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Playback and preview
    # ------------------------------------------------------------------

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
        path = self._resolve_asset_path(reference)
        try:
            self.preview_texture = self.game.engine.assets.texture(path)
            self.preview_reference = reference
            self.preview_error = ""
        except Exception as exc:
            self.preview_texture = None
            self.preview_reference = reference
            self.preview_error = str(exc)

    # ------------------------------------------------------------------
    # Editor audio playback
    # ------------------------------------------------------------------

    def _resolve_audio_path(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        normalized = str(path).replace("\\", "/")
        normalized_lower = normalized.lower()
        for prefix in ("mygame/assets/", "assets/"):
            if normalized_lower.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        return self.project_context.resolve_asset(
            normalized,
            reference=self.requested_cutscene_path,
        )

    def _audio_reference(self, value: str) -> str:
        return str(self._resolve_audio_path(value).resolve())

    @staticmethod
    def _audio_path_from_value(value: object) -> str:
        if not isinstance(value, dict):
            return ""
        return str(
            value.get("path", value.get("asset", value.get("source", "")))
            or ""
        ).strip()

    def _preload_audio_tracks(self) -> None:
        self._audio_cache.clear()
        audio = self.game.audio
        for track in self.asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                value = frame.value
                if not isinstance(value, dict):
                    continue
                path = self._audio_path_from_value(value)
                if not path:
                    continue
                if str(value.get("action", "play")).lower() in {"stop", "fade_out"}:
                    continue
                reference = self._audio_reference(path)
                if reference in self._audio_cache:
                    continue
                try:
                    loader = audio.load_stream if bool(value.get("stream", False)) else audio.load
                    self._audio_cache[reference] = loader(reference)
                except Exception as exc:
                    self.status = f"Audio unavailable: {Path(path).name} ({exc})"

    def _play_editor_audio(self, value: object, *, offset: float = 0.0) -> None:
        if not isinstance(value, dict):
            return
        path = self._audio_path_from_value(value)
        if not path:
            return

        audio = self.game.audio
        reference = self._audio_reference(path)
        action = str(value.get("action", "play")).lower()
        active = self._audio_sources.get(reference, [])
        if action in {"stop", "fade_out"}:
            for source in tuple(active):
                if action == "fade_out":
                    source.fade_out(max(0.0, _float(value.get("duration", 0.0))))
                else:
                    source.stop()
            return

        sound = self._audio_cache.get(reference)
        if sound is None:
            try:
                loader = audio.load_stream if bool(value.get("stream", False)) else audio.load
                sound = loader(reference)
                self._audio_cache[reference] = sound
            except Exception as exc:
                self.status = f"Could not play audio: {Path(path).name} ({exc})"
                return

        channel_name = str(value.get("channel", "sfx")).lower()
        channel = next((item for item in AudioChannel if item.value == channel_name), AudioChannel.SFX)
        bus_name = str(value.get("bus", channel_name.title()))
        try:
            bus = audio.get_bus(bus_name)
        except KeyError:
            bus = None
        source = AudioSource(
            sound,
            channel=channel,
            volume=max(0.0, min(1.0, _float(value.get("volume", 1.0), 1.0))),
            loop=bool(value.get("loop", False)),
            bus=bus,
        )
        audio.player.play(source)
        if offset > 0.0:
            duration = max(0.0, _float(getattr(sound, "duration", 0.0)))
            if bool(value.get("loop", False)) and duration > 0.0:
                offset %= duration
            if offset > 0.0:
                source.seek_seconds(offset)
        self._audio_sources.setdefault(reference, []).append(source)
        fade_in = _float(value.get("fade_in", 0.0), 0.0)
        if fade_in > 0.0:
            source.fade_in(fade_in)

    def _start_audio_at_playhead(self) -> None:
        """Start sounds that are already active at the current playhead."""

        states: dict[str, tuple[dict, float]] = {}
        frames: list[tuple[float, dict]] = []
        for track in self.asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                if frame.time <= self.player.time and isinstance(frame.value, dict):
                    frames.append((frame.time, frame.value))

        for frame_time, value in sorted(frames, key=lambda item: item[0]):
            path = self._audio_path_from_value(value)
            if not path:
                continue
            reference = self._audio_reference(path)
            action = str(value.get("action", "play")).lower()
            if action in {"stop", "fade_out"}:
                states.pop(reference, None)
            else:
                states[reference] = (value, frame_time)

        for value, frame_time in states.values():
            path = self._audio_path_from_value(value)
            reference = self._audio_reference(path)
            sound = self._audio_cache.get(reference)
            if sound is None:
                continue
            offset = max(0.0, self.player.time - frame_time)
            duration = max(0.0, _float(getattr(sound, "duration", 0.0)))
            if not bool(value.get("loop", False)) and duration > 0.0 and offset >= duration:
                continue
            self._play_editor_audio(value, offset=offset)

    def _trigger_audio_between(self, start: float, end: float) -> None:
        if end < start:
            return
        for track in self.asset.tracks:
            if not track.enabled or track.track_type != "audio":
                continue
            for frame in track.keyframes:
                if start < frame.time <= end:
                    self._play_editor_audio(frame.value)

    def _prune_editor_audio(self) -> None:
        audio = self.game.audio
        for reference, sources in tuple(self._audio_sources.items()):
            alive = []
            for source in sources:
                if source.stopped:
                    audio.player.remove(source)
                else:
                    alive.append(source)
            if alive:
                self._audio_sources[reference] = alive
            else:
                self._audio_sources.pop(reference, None)

    def _pause_editor_audio(self) -> None:
        for sources in self._audio_sources.values():
            for source in sources:
                source.pause()

    def _resume_editor_audio(self) -> None:
        for sources in self._audio_sources.values():
            for source in sources:
                source.resume()

    def _stop_editor_audio(self) -> None:
        if self.game.engine is None:
            self._audio_cache.clear()
            self._audio_sources.clear()
            return
        audio = self.game.audio
        for sources in self._audio_sources.values():
            for source in sources:
                source.stop()
                audio.player.remove(source)
        self._audio_sources.clear()
        self._audio_cache.clear()

    # ------------------------------------------------------------------
    # Camera editing
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Browser and dialogs
    # ------------------------------------------------------------------

    def _open_browser(self, mode: str) -> None:
        self.modal = "browser"
        self.browser_mode = mode
        self.browser_name.visible = mode == "save"
        self.browser_action_button.visible = mode == "save"
        self.browser_root = self.project_path
        if mode in {"image", "audio"}:
            start = self.assets_root
        elif mode == "save" and (self.project_path / "cutscenes").is_dir():
            start = self.project_path / "cutscenes"
        else:
            start = self.project_path
        extensions = {
            "image": IMAGE_EXTENSIONS,
            "audio": AUDIO_EXTENSIONS,
        }.get(mode, (CUTSCENE_ASSET_SUFFIX,))
        self.file_browser.open(self.project_path, start=start, extensions=extensions)
        self.browser_path = self.file_browser.path
        self.browser_name.set_text(f"{self.document_name}{CUTSCENE_ASSET_SUFFIX}" if mode == "save" else "")
        self._refresh_browser()

    def _refresh_browser(self) -> None:
        self.file_browser.refresh()
        self.browser_path = self.file_browser.path
        self.browser_entries = list(self.file_browser.entries)
        sync_browser_list(self.file_browser, self.browser_list)

    def _browser_selected(self, index: int) -> None:
        path = self.file_browser.select(index)
        self._refresh_browser()
        if path is None:
            return
        if self.browser_mode == "open":
            self._load_asset(path)
            self._close_modal()
        elif self.browser_mode == "save":
            self.browser_name.set_text(path.name)
            self.status = f"Save as {path.name}"
        elif self.browser_mode == "image":
            self.key_value_field.set_text(self._asset_relative(path))
            self._apply_selected_properties()
            self._close_modal()
        elif self.browser_mode == "audio":
            self.key_value_field.set_text(self._asset_relative(path))
            self._apply_selected_properties()
            self._close_modal()

    def _browser_action(self) -> None:
        name = self.browser_name.text.strip() or f"{self.document_name}{CUTSCENE_ASSET_SUFFIX}"
        if not name.lower().endswith(CUTSCENE_ASSET_SUFFIX):
            name += CUTSCENE_ASSET_SUFFIX
        self._save_asset(self.browser_path / name)
        self._close_modal()

    def _browse_key_asset(self) -> None:
        track = self._active_track()
        if track is not None:
            self._open_browser("audio" if track.track_type == "audio" else "image")

    def _close_modal(self) -> None:
        self.modal = None
        self.status = "Ready"

    def _menu_opened(self, opened: Menu) -> None:
        close_other_menus(self.menus, opened)

    def _show_help(self) -> None:
        self.modal = "info"
        self.info_title = "Cutscene Editor Help"
        self.info_lines = (
            "Space: Play / pause     Left click timeline: move playhead",
            "Add Keyframe: create a value at the current playhead time",
            "Image tracks use project-relative paths inside the assets folder.",
            "Events store callback IDs and parameters, never Python functions.",
        )

    def _show_about(self) -> None:
        self.modal = "info"
        self.info_title = "About Nexora Cutscene Editor"
        self.info_lines = (
            "Data-driven cinematic authoring for Nexora Engine.",
            "Cutscenes are stored as signed .ncutscene assets.",
            "Runtime playback uses the same timeline data as the editor.",
        )

    # ------------------------------------------------------------------
    # Layout and input
    # ------------------------------------------------------------------

    def _layout(self) -> tuple[float, float]:
        width = float(self.game.renderer.width)
        height = float(self.game.renderer.height)
        if (width, height) == self._layout_size:
            return width, height
        self._layout_size = (width, height)
        content_bottom = height - self.STATUS_HEIGHT
        timeline_top = content_bottom - self.TIMELINE_HEIGHT
        content_height = timeline_top - self.TOOLBAR_HEIGHT
        self.left_panel = Rect(0.0, self.TOOLBAR_HEIGHT, self.LEFT_WIDTH, content_height)
        self.right_panel = Rect(width - self.RIGHT_WIDTH, self.TOOLBAR_HEIGHT, self.RIGHT_WIDTH, content_height)
        self.viewport = Rect(self.LEFT_WIDTH, self.TOOLBAR_HEIGHT, width - self.LEFT_WIDTH - self.RIGHT_WIDTH, content_height)
        self.timeline = Rect(0.0, timeline_top, width, self.TIMELINE_HEIGHT)

        self.file_menu.rect = Rect(12.0, 9.0, 82.0, 40.0)
        self.cutscene_menu.rect = Rect(100.0, 9.0, 120.0, 40.0)
        self.view_menu.rect = Rect(226.0, 9.0, 88.0, 40.0)
        self.help_menu.rect = Rect(320.0, 9.0, 82.0, 40.0)

        self.track_list.rect = Rect(self.left_panel.x + 10.0, self.left_panel.y + 48.0, self.left_panel.width - 20.0, self.left_panel.height - 114.0)
        self.add_track_button.rect = Rect(self.left_panel.x + 10.0, self.left_panel.y + self.left_panel.height - 58.0, (self.left_panel.width - 25.0) / 2.0, 38.0)
        self.remove_track_button.rect = Rect(self.left_panel.x + self.left_panel.width / 2.0 + 2.5, self.left_panel.y + self.left_panel.height - 58.0, (self.left_panel.width - 25.0) / 2.0, 38.0)

        right_x = self.right_panel.x + 14.0
        right_width = self.right_panel.width - 28.0
        half = (right_width - 10.0) / 2.0
        self.document_field.rect = Rect(right_x, self.right_panel.y + 54.0, right_width, 34.0)
        self.duration_field.rect = Rect(right_x, self.right_panel.y + 122.0, half, 34.0)
        self.fps_field.rect = Rect(right_x + half + 10.0, self.right_panel.y + 122.0, half, 34.0)
        self.track_name_field.rect = Rect(right_x, self.right_panel.y + 208.0, right_width, 34.0)
        self.track_type.rect = Rect(right_x, self.right_panel.y + 264.0, right_width, 34.0)
        self.track_enabled.rect = Rect(right_x, self.right_panel.y + 306.0, right_width, 28.0)
        self.key_time_field.rect = Rect(right_x, self.right_panel.y + 390.0, half, 34.0)
        self.key_interpolation.rect = Rect(right_x + half + 10.0, self.right_panel.y + 390.0, half, 34.0)
        self.key_value_field.rect = Rect(right_x, self.right_panel.y + 446.0, right_width - 94.0, 34.0)
        self.key_browse_button.rect = Rect(right_x + right_width - 84.0, self.right_panel.y + 446.0, 84.0, 34.0)
        self.key_x_field.rect = Rect(right_x, self.right_panel.y + 500.0, half, 34.0)
        self.key_y_field.rect = Rect(right_x + half + 10.0, self.right_panel.y + 500.0, half, 34.0)
        self.key_zoom_field.rect = Rect(right_x, self.right_panel.y + 544.0, half, 34.0)
        self.key_alpha_field.rect = Rect(right_x + half + 10.0, self.right_panel.y + 544.0, half, 34.0)
        self.key_volume_field.rect = Rect(right_x, self.right_panel.y + 500.0, half, 34.0)

        button_y = self.timeline.y + 5.0
        button_x = self.timeline.x + self.timeline_label_width + 10.0
        self.play_button.rect = Rect(button_x, button_y, 78.0, 32.0)
        self.pause_button.rect = Rect(button_x + 84.0, button_y, 78.0, 32.0)
        self.stop_button.rect = Rect(button_x + 168.0, button_y, 78.0, 32.0)
        self.add_keyframe_button.rect = Rect(button_x + 252.0, button_y, 132.0, 32.0)
        self.delete_keyframe_button.rect = Rect(button_x + 392.0, button_y, 142.0, 32.0)
        self.insert_image_button.rect = Rect(button_x + 542.0, button_y, 124.0, 32.0)
        self.camera_keyframe_button.rect = Rect(button_x + 676.0, button_y, 142.0, 32.0)
        return width, height

    def _focus_fields(self, fields: list[TextField], input_manager, mouse_x: float, mouse_y: float) -> None:
        if not input_manager.mouse_pressed("left"):
            return
        clicked = next((field for field in fields if field.visible and field.rect.contains(mouse_x, mouse_y)), None)
        for field in fields:
            if field is not clicked:
                field.blur(input_manager)

    def _update_controls(self, controls: list, input_manager, mouse_x: float, mouse_y: float) -> None:
        fields = [control for control in controls if isinstance(control, TextField)]
        self._focus_fields(fields, input_manager, mouse_x, mouse_y)
        for control in controls:
            control.update(input_manager, mouse_x, mouse_y)

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

    def update(self, delta_time: float) -> None:
        self._layout()
        input_manager = self.game.input
        mouse_x, mouse_y = input_manager.mouse_position
        if self.modal == "browser":
            self._update_controls([self.browser_list, self.browser_name, self.browser_cancel_button, self.browser_action_button], input_manager, mouse_x, mouse_y)
            return
        if self.modal == "info":
            self._update_controls([self.info_close_button], input_manager, mouse_x, mouse_y)
            return

        menu_was_open = any(menu.open for menu in self.menus)
        self._update_controls(self.menus, input_manager, mouse_x, mouse_y)
        if menu_was_open or any(menu.open for menu in self.menus):
            return

        controls = [
            self.track_list,
            self.add_track_button,
            self.remove_track_button,
            self.document_field,
            self.duration_field,
            self.fps_field,
            self.track_name_field,
            self.track_type,
            self.track_enabled,
            self.key_time_field,
            self.key_value_field,
            self.key_x_field,
            self.key_y_field,
            self.key_zoom_field,
            self.key_alpha_field,
            self.key_volume_field,
            self.key_interpolation,
            self.key_browse_button,
            self.play_button,
            self.pause_button,
            self.stop_button,
            self.add_keyframe_button,
            self.delete_keyframe_button,
            self.insert_image_button,
            self.camera_keyframe_button,
        ]
        self._update_controls(controls, input_manager, mouse_x, mouse_y)
        self._update_camera_viewport(input_manager, mouse_x, mouse_y)
        self._update_timeline(input_manager, mouse_x, mouse_y)
        if input_manager.key_pressed("space"):
            self._toggle_playback()
        previous_time = self.player.time
        self.player.update(delta_time)
        self.current_time = self.player.time
        if self.player.playing or self.player.time > previous_time:
            self._trigger_audio_between(previous_time, self.player.time)
            self._audio_last_time = self.player.time
        self._prune_editor_audio()
        self._refresh_preview_texture()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _renderer_point(self, x: float, y: float) -> tuple[float, float]:
        return x - self.game.renderer.width / 2.0, y - self.game.renderer.height / 2.0

    def _render_preview(self, renderer, viewport_size: tuple[float, float]) -> None:
        draw_rect(renderer, self.viewport, self.theme.background, viewport_size)
        preview_width = min(self.viewport.width - 60.0, 720.0)
        preview_height = preview_width * 9.0 / 16.0
        if preview_height > self.viewport.height - 90.0:
            preview_height = self.viewport.height - 90.0
            preview_width = preview_height * 16.0 / 9.0
        center_x = self.viewport.x + self.viewport.width / 2.0
        center_y = self.viewport.y + self.viewport.height / 2.0 + 12.0
        frame_rect = Rect(center_x - preview_width / 2.0, center_y - preview_height / 2.0, preview_width, preview_height)
        draw_rect(renderer, frame_rect, (10, 12, 16, 255), viewport_size)
        if self.preview_texture is not None:
            camera = self._current_value("camera")
            zoom = max(0.05, min(4.0, _float(camera.get("zoom", 1.0), 1.0)))
            camera_x = _float(camera.get("x", 0.0))
            camera_y = _float(camera.get("y", 0.0))
            preview_scale = preview_width / 640.0
            draw_x = center_x - camera_x * preview_scale * zoom
            draw_y = center_y - camera_y * preview_scale * zoom
            draw_x, draw_y = self._renderer_point(draw_x, draw_y)
            renderer.sprite(self.preview_texture, draw_x, draw_y, width=preview_width * zoom, height=preview_height * zoom, alpha=1.0)
        elif self.preview_error:
            draw_text(renderer, "Could not load preview", center_x, center_y - 12.0, viewport_size, scale=0.72, color=self.theme.error, align="center")
        else:
            draw_text(renderer, "Add an image keyframe to preview", center_x, center_y - 12.0, viewport_size, scale=0.72, color=self.theme.muted, align="center")
        fade = self._current_value("fade")
        alpha = max(0.0, min(1.0, _float(fade.get("alpha", 0.0))))
        if alpha > 0.0:
            color = fade.get("color", [0.0, 0.0, 0.0])
            if not isinstance(color, (list, tuple)) or len(color) < 3:
                color = (0.0, 0.0, 0.0)
            draw_rect(
                renderer,
                frame_rect,
                (int(max(0.0, min(1.0, color[0])) * 255.0), int(max(0.0, min(1.0, color[1])) * 255.0), int(max(0.0, min(1.0, color[2])) * 255.0), int(alpha * 255.0)),
                viewport_size,
            )
        draw_text(renderer, "MMB drag: camera pan   Wheel: zoom", self.viewport.x + 14.0, self.viewport.y + self.viewport.height - 18.0, viewport_size, scale=0.42, color=self.theme.muted)
        draw_outline(renderer, frame_rect, self.theme.border, viewport_size)

    def _render_main_ui(self, renderer, viewport_size: tuple[float, float]) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0.0, 0.0, width, self.TOOLBAR_HEIGHT), self.theme.panel, viewport_size)
        draw_rect(renderer, self.left_panel, self.theme.panel, viewport_size)
        draw_rect(renderer, self.right_panel, self.theme.panel, viewport_size)
        draw_rect(renderer, self.timeline, self.theme.panel_dark, viewport_size)
        draw_rect(renderer, Rect(0.0, height - self.STATUS_HEIGHT, width, self.STATUS_HEIGHT), self.theme.panel, viewport_size)
        for rect in (Rect(0, 0, width, self.TOOLBAR_HEIGHT), self.left_panel, self.viewport, self.right_panel, self.timeline):
            draw_outline(renderer, rect, self.theme.border, viewport_size)

        draw_text(renderer, f"{self.document_name}{' *' if self.dirty else ''}", width - 16.0, 18.0, viewport_size, scale=0.64, color=self.theme.muted, align="right")
        draw_text(renderer, "Tracks", self.left_panel.x + 12.0, self.left_panel.y + 14.0, viewport_size, scale=0.78)
        draw_text(renderer, "Live Preview", self.viewport.x + 12.0, self.viewport.y + 14.0, viewport_size, scale=0.78)
        draw_text(renderer, f"Time {self.current_time:.2f}s / {self.asset.duration:.2f}s", self.viewport.x + self.viewport.width - 12.0, self.viewport.y + 16.0, viewport_size, scale=0.50, color=self.theme.muted, align="right")
        draw_text(renderer, "Cutscene Properties", self.right_panel.x + 14.0, self.right_panel.y + 14.0, viewport_size, scale=0.78)
        draw_text(renderer, "Name", self.right_panel.x + 14.0, self.right_panel.y + 40.0, viewport_size, scale=0.44, color=self.theme.muted)
        draw_text(renderer, "Duration", self.right_panel.x + 14.0, self.right_panel.y + 108.0, viewport_size, scale=0.44, color=self.theme.muted)
        draw_text(renderer, "FPS", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 108.0, viewport_size, scale=0.44, color=self.theme.muted)
        draw_text(renderer, "Selected Track", self.right_panel.x + 14.0, self.right_panel.y + 164.0, viewport_size, scale=0.64)
        draw_text(renderer, "Track Name", self.right_panel.x + 14.0, self.right_panel.y + 190.0, viewport_size, scale=0.38, color=self.theme.muted)
        draw_text(renderer, "Track Type", self.right_panel.x + 14.0, self.right_panel.y + 246.0, viewport_size, scale=0.38, color=self.theme.muted)
        draw_text(renderer, "Selected Keyframe", self.right_panel.x + 14.0, self.right_panel.y + 344.0, viewport_size, scale=0.64)
        draw_text(renderer, "Time", self.right_panel.x + 14.0, self.right_panel.y + 372.0, viewport_size, scale=0.38, color=self.theme.muted)
        draw_text(renderer, "Interpolation", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 372.0, viewport_size, scale=0.38, color=self.theme.muted)
        draw_text(renderer, "Value / Asset", self.right_panel.x + 14.0, self.right_panel.y + 428.0, viewport_size, scale=0.38, color=self.theme.muted)
        track = self._active_track()
        track_type = track.track_type if track else ""
        if track_type == "camera":
            draw_text(renderer, "X", self.right_panel.x + 14.0, self.right_panel.y + 484.0, viewport_size, scale=0.44, color=self.theme.muted)
            draw_text(renderer, "Y", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 484.0, viewport_size, scale=0.44, color=self.theme.muted)
            draw_text(renderer, "Zoom", self.right_panel.x + 14.0, self.right_panel.y + 528.0, viewport_size, scale=0.44, color=self.theme.muted)
        elif track_type == "fade":
            draw_text(renderer, "Alpha", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 528.0, viewport_size, scale=0.44, color=self.theme.muted)
        elif track_type == "audio":
            draw_text(renderer, "Volume", self.right_panel.x + 14.0, self.right_panel.y + 484.0, viewport_size, scale=0.44, color=self.theme.muted)

        self.track_list.render(renderer, viewport_size, self.theme)
        self.add_track_button.render(renderer, viewport_size, self.theme)
        self.remove_track_button.render(renderer, viewport_size, self.theme)
        for control in (
            self.document_field,
            self.duration_field,
            self.fps_field,
            self.track_name_field,
            self.track_type,
            self.track_enabled,
            self.key_time_field,
            self.key_value_field,
            self.key_x_field,
            self.key_y_field,
            self.key_zoom_field,
            self.key_alpha_field,
            self.key_volume_field,
            self.key_interpolation,
            self.key_browse_button,
        ):
            control.render(renderer, viewport_size, self.theme)
        self._render_timeline(renderer, viewport_size)

        # Dropdowns extend below the toolbar.  Render menus last so no panel,
        # timeline control or viewport element can cover an open menu.
        for menu in self.menus:
            menu.render(renderer, viewport_size, self.theme)

        draw_text(renderer, self.status, 12.0, height - self.STATUS_HEIGHT + 7.0, viewport_size, scale=0.56, color=self.theme.muted)
        draw_text(renderer, "Nexora Cutscene Editor", width - 12.0, height - self.STATUS_HEIGHT + 7.0, viewport_size, scale=0.56, color=self.theme.muted, align="right")

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

    def _render_browser(self, renderer, viewport_size: tuple[float, float]) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport_size)
        window = Rect(150.0, 70.0, width - 300.0, height - 140.0)
        draw_rect(renderer, window, self.theme.panel, viewport_size, radius=6.0)
        draw_outline(renderer, window, self.theme.border, viewport_size)
        titles = {"open": "Open Cutscene", "save": "Save Cutscene As", "image": "Choose Image Asset", "audio": "Choose Audio Asset"}
        draw_text(renderer, titles.get(self.browser_mode, "Choose Asset"), window.x + 18.0, window.y + 16.0, viewport_size, scale=0.80)
        draw_text(renderer, str(self.browser_path), window.x + 18.0, window.y + 50.0, viewport_size, scale=0.48, color=self.theme.muted)
        self.browser_list.rect = Rect(window.x + 18.0, window.y + 78.0, window.width - 36.0, window.height - 150.0)
        self.browser_list.render(renderer, viewport_size, self.theme)
        self.browser_cancel_button.rect = Rect(window.x + window.width - 126.0, window.y + window.height - 48.0, 108.0, 32.0)
        self.browser_cancel_button.render(renderer, viewport_size, self.theme)
        if self.browser_mode == "save":
            draw_text(renderer, "File name", window.x + 18.0, window.y + window.height - 70.0, viewport_size, scale=0.46, color=self.theme.muted)
            self.browser_name.rect = Rect(window.x + 86.0, window.y + window.height - 78.0, window.width - 350.0, 34.0)
            self.browser_name.render(renderer, viewport_size, self.theme)
            self.browser_action_button.rect = Rect(window.x + window.width - 244.0, window.y + window.height - 48.0, 108.0, 32.0)
            self.browser_action_button.render(renderer, viewport_size, self.theme)

    def _render_info(self, renderer, viewport_size: tuple[float, float]) -> None:
        width, height = viewport_size
        draw_rect(renderer, Rect(0, 0, width, height), (0, 0, 0, 175), viewport_size)
        window = centered_rect(viewport_size, 720.0, 340.0)
        draw_rect(renderer, window, self.theme.panel, viewport_size, radius=6.0)
        draw_outline(renderer, window, self.theme.border, viewport_size)
        draw_text(renderer, self.info_title, window.x + 22.0, window.y + 20.0, viewport_size, scale=0.86)
        y = window.y + 82.0
        for line in self.info_lines:
            draw_text(renderer, line, window.x + 24.0, y, viewport_size, scale=0.60, color=self.theme.text)
            y += 40.0
        self.info_close_button.rect = Rect(window.x + window.width - 126.0, window.y + window.height - 50.0, 108.0, 32.0)
        self.info_close_button.render(renderer, viewport_size, self.theme)

    def render(self, interpolation: float) -> None:
        del interpolation
        width, height = self._layout()
        renderer = self.game.renderer
        viewport_size = (width, height)
        self._render_preview(renderer, viewport_size)
        with renderer.overlay_scope():
            self._render_main_ui(renderer, viewport_size)
            if self.modal == "browser":
                self._render_browser(renderer, viewport_size)
            elif self.modal == "info":
                self._render_info(renderer, viewport_size)


class CutsceneEditorApp(Game):
    """Application wrapper for the standalone Cutscene Editor."""

    def __init__(self, *, project_path: str | Path | None = None, cutscene_path: str | Path | None = None) -> None:
        self.cutscene_project_path = resolve_project_path(project_path)
        self.cutscene_project_context = EditorProjectContext.from_path(self.cutscene_project_path)
        self.cutscene_asset_path = cutscene_path
        super().__init__(
            project_name="NexoraStandaloneCutsceneEditor",
            title=f"Nexora Cutscene Editor - {self.cutscene_project_path.name}",
            width=1600,
            height=960,
            resizable=True,
            editor_mode=True,
        )
        self.editor_scene: CutsceneEditorScene | None = None

    def initialize(self) -> None:
        if self.engine is not None:
            self.engine.assets.root = self.cutscene_project_context.asset_root_for(
                self.cutscene_asset_path
            )
        icon_path = self.cutscene_project_context.asset_root_for(
            self.cutscene_asset_path
        ) / "icon.png"
        if self.window is not None and icon_path is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                pass
        scene = CutsceneEditorScene(
            self,
            self.cutscene_project_path,
            self.cutscene_asset_path,
            self.cutscene_project_context,
        )
        self.editor_scene = scene
        self.scene = scene


def run_cutscene_editor(project_path: str | Path | None = None, cutscene_path: str | Path | None = None) -> int:
    try:
        CutsceneEditorApp(project_path=project_path, cutscene_path=cutscene_path).run()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"[Nexora Cutscene Editor] {exc}")
        return 2
    return 0


__all__ = ["CutsceneEditorApp", "CutsceneEditorScene", "run_cutscene_editor"]
