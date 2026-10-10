from __future__ import annotations

"""Standalone timeline editor for Nexora ``.ncutscene`` assets."""

from pathlib import Path

from nexora.gameplay.cutscene import (
    CUTSCENE_ASSET_SUFFIX,
    CutsceneAsset,
    CutscenePlayer,
    INTERPOLATIONS,
    TRACK_TYPES,
)
from nexora.editor.base_editor import EditorBaseScene
from nexora.editor.model import EditorProjectContext
from nexora.editor.standalone_app import StandaloneEditorApp, run_standalone_editor
from nexora.editor.ui import (
    Button,
    CheckBox,
    Dropdown,
    FormLayout,
    layout_equal_row,
    layout_fixed_row,
    ListBox,
    Menu,
    Rect,
    TextField,
    draw_outline,
    draw_rect,
    draw_text,
    render_document_title,
    render_editor_shell,
    render_form_label,
    render_section_title,
    render_status_bar,
)


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
AUDIO_EXTENSIONS = (".wav", ".ogg", ".mp3", ".flac")
DEFAULT_SIGNING_KEY = (
    b"nexora-default-save-signing-key-"
    b"change-this-for-your-game"
)


from .cutscene_common import parse_float as _float
from .cutscene_document import CutsceneDocumentMixin
from .cutscene_playback import CutscenePlaybackMixin
from .cutscene_audio import CutsceneAudioMixin
from .cutscene_camera import CutsceneCameraMixin
from .cutscene_timeline import CutsceneTimelineMixin



class CutsceneEditorScene(
    CutsceneDocumentMixin,
    CutscenePlaybackMixin,
    CutsceneAudioMixin,
    CutsceneCameraMixin,
    CutsceneTimelineMixin,
    EditorBaseScene,
):
    """Renderer-backed cutscene editor with a timeline and live preview."""

    MODAL_CLOSE_STATUS = "Ready"

    TOOLBAR_HEIGHT = EditorBaseScene.TOOLBAR_HEIGHT
    STATUS_HEIGHT = EditorBaseScene.STATUS_HEIGHT
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

        self.asset = CutsceneAsset()
        self.player = CutscenePlayer(self.asset, on_event=self._event_fired)
        self.document_path: Path | None = None
        self.document_name = "Untitled"
        self.dirty = False
        self.status = "Ready"
        self.browser_mode = "open"
        self.browser_root = self.project_path
        self.browser_path = self.project_path
        self.preview_texture = None
        self.preview_reference = ""
        self.preview_error = ""
        self._audio_cache: dict[str, object] = {}
        self._audio_sources: dict[str, list[object]] = {}
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
        self._set_menus([self.file_menu, self.cutscene_menu, self.view_menu, self.help_menu])

        self.new_cutscene()
        if cutscene_path is not None:
            self._load_asset(self._resolve_requested_path(cutscene_path))

    # ------------------------------------------------------------------
    # Asset and document paths
    # ------------------------------------------------------------------

    def _asset_reference(self) -> str | Path | None:
        return self.requested_cutscene_path

    def _resolve_requested_path(self, value: str | Path) -> Path:
        return self._project_file_path(
            value,
            roots=(self.project_context.cutscenes_root,),
        )

    def _signing_key(self):
        return getattr(self.game, "_scene_signing_key", DEFAULT_SIGNING_KEY)



    # ------------------------------------------------------------------
    # Browser and dialogs
    # ------------------------------------------------------------------

    def _open_browser(self, mode: str) -> None:
        self.browser_name.visible = mode == "save"
        self.browser_action_button.visible = mode == "save"
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
        self._open_file_browser(
            mode,
            root=self.project_path,
            start=start,
            extensions=extensions,
            filename=f"{self.document_name}{CUTSCENE_ASSET_SUFFIX}" if mode == "save" else "",
        )

    def _browser_selected(self, index: int) -> None:
        path = self._select_browser_entry(index)
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

    def _show_help(self) -> None:
        self._open_info_dialog(
            "Cutscene Editor Help",
            (
                "Space: Play / pause     Left click timeline: move playhead",
                "Add Keyframe: create a value at the current playhead time",
                "Image tracks use project-relative paths inside the assets folder.",
                "Events store callback IDs and parameters, never Python functions.",
            ),
        )

    def _show_about(self) -> None:
        self._open_info_dialog(
            "About Nexora Cutscene Editor",
            (
                "Data-driven cinematic authoring for Nexora Engine.",
                "Cutscenes are stored as signed .ncutscene assets.",
                "Runtime playback uses the same timeline data as the editor.",
            ),
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

        layout_fixed_row(
            (self.file_menu, self.cutscene_menu, self.view_menu, self.help_menu),
            (82.0, 120.0, 88.0, 82.0),
            x=105.0,
            y=5.0,
            height=38.0,
            gap=6.0,
        )

        self.track_list.rect = Rect(self.left_panel.x + 10.0, self.left_panel.y + 48.0, self.left_panel.width - 20.0, self.left_panel.height - 114.0)
        layout_equal_row(
            (self.add_track_button, self.remove_track_button),
            x=self.left_panel.x + 10.0,
            y=self.left_panel.y + self.left_panel.height - 58.0,
            width=self.left_panel.width - 20.0,
            height=38.0,
            gap=5.0,
        )

        right_x = self.right_panel.x + 14.0
        right_width = self.right_panel.width - 28.0
        right_form = FormLayout(
            x=right_x,
            y=self.right_panel.y,
            width=right_width,
            columns=2,
            column_gap=10.0,
            control_height=34.0,
            label_gap=0.0,
        )
        half = right_form.column_width
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
        layout_fixed_row(
            (
                self.play_button,
                self.pause_button,
                self.stop_button,
                self.add_keyframe_button,
                self.delete_keyframe_button,
                self.insert_image_button,
                self.camera_keyframe_button,
            ),
            (78.0, 78.0, 78.0, 132.0, 142.0, 124.0, 142.0),
            x=button_x,
            y=button_y,
            height=32.0,
            gap=(6.0, 6.0, 6.0, 8.0, 8.0, 10.0),
        )
        return width, height




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
        render_editor_shell(
            renderer,
            viewport_size,
            self.theme,
            toolbar_height=self.TOOLBAR_HEIGHT,
            status_height=self.STATUS_HEIGHT,
            panels=(
                (self.left_panel, self.theme.panel),
                (self.right_panel, self.theme.panel),
                (self.timeline, self.theme.panel_dark),
            ),
            outline_rects=(self.left_panel, self.viewport, self.right_panel, self.timeline),
        )
        render_document_title(
            renderer,
            viewport_size,
            self.theme,
            self.document_name,
            dirty=self.dirty,
            scale=0.64,
        )
        render_section_title(
            renderer,
            viewport_size,
            self.theme,
            self.left_panel,
            "Tracks",
            scale=0.78,
        )
        render_section_title(
            renderer,
            viewport_size,
            self.theme,
            self.viewport,
            "Live Preview",
            scale=0.78,
        )
        draw_text(renderer, f"Time {self.current_time:.2f}s / {self.asset.duration:.2f}s", self.viewport.x + self.viewport.width - 12.0, self.viewport.y + 16.0, viewport_size, scale=0.50, color=self.theme.muted, align="right")
        render_section_title(
            renderer,
            viewport_size,
            self.theme,
            self.right_panel,
            "Cutscene Properties",
            x_offset=14.0,
            scale=0.78,
        )
        render_form_label(renderer, viewport_size, self.theme, "Name", self.right_panel.x + 14.0, self.right_panel.y + 40.0)
        render_form_label(renderer, viewport_size, self.theme, "Duration", self.right_panel.x + 14.0, self.right_panel.y + 108.0)
        render_form_label(renderer, viewport_size, self.theme, "FPS", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 108.0)
        render_section_title(renderer, viewport_size, self.theme, self.right_panel, "Selected Track", x_offset=14.0, y_offset=164.0, scale=0.64)
        render_form_label(renderer, viewport_size, self.theme, "Track Name", self.right_panel.x + 14.0, self.right_panel.y + 190.0, scale=0.38)
        render_form_label(renderer, viewport_size, self.theme, "Track Type", self.right_panel.x + 14.0, self.right_panel.y + 246.0, scale=0.38)
        render_section_title(renderer, viewport_size, self.theme, self.right_panel, "Selected Keyframe", x_offset=14.0, y_offset=344.0, scale=0.64)
        render_form_label(renderer, viewport_size, self.theme, "Time", self.right_panel.x + 14.0, self.right_panel.y + 372.0, scale=0.38)
        render_form_label(renderer, viewport_size, self.theme, "Interpolation", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 372.0, scale=0.38)
        render_form_label(renderer, viewport_size, self.theme, "Value / Asset", self.right_panel.x + 14.0, self.right_panel.y + 428.0, scale=0.38)
        track = self._active_track()
        track_type = track.track_type if track else ""
        if track_type == "camera":
            render_form_label(renderer, viewport_size, self.theme, "X", self.right_panel.x + 14.0, self.right_panel.y + 484.0)
            render_form_label(renderer, viewport_size, self.theme, "Y", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 484.0)
            render_form_label(renderer, viewport_size, self.theme, "Zoom", self.right_panel.x + 14.0, self.right_panel.y + 528.0)
        elif track_type == "fade":
            render_form_label(renderer, viewport_size, self.theme, "Alpha", self.right_panel.x + self.right_panel.width / 2.0 + 5.0, self.right_panel.y + 528.0)
        elif track_type == "audio":
            render_form_label(renderer, viewport_size, self.theme, "Volume", self.right_panel.x + 14.0, self.right_panel.y + 484.0)

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

        render_status_bar(
            renderer,
            viewport_size,
            self.theme,
            self.status,
            "Nexora Cutscene Editor",
            status_height=self.STATUS_HEIGHT,
        )


    def _render_browser(self, renderer, viewport_size: tuple[float, float]) -> None:
        titles = {
            "open": "Open Cutscene",
            "save": "Save Cutscene As",
            "image": "Choose Image Asset",
            "audio": "Choose Audio Asset",
        }
        self._render_file_dialog(
            renderer,
            viewport_size,
            title=titles.get(self.browser_mode, "Choose Asset"),
            margin_y=70.0,
        )

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
                self._render_info_dialog(renderer, viewport_size, width=720.0, height=340.0, line_step=40.0)


class CutsceneEditorApp(StandaloneEditorApp[CutsceneEditorScene]):
    """Application wrapper for the standalone Cutscene Editor."""

    PROJECT_NAME = "NexoraStandaloneCutsceneEditor"
    WINDOW_TITLE = "Nexora Cutscene Editor"
    WINDOW_WIDTH = 1600
    WINDOW_HEIGHT = 960
    ERROR_PREFIX = "Nexora Cutscene Editor"

    def __init__(self, *, project_path: str | Path | None = None, cutscene_path: str | Path | None = None) -> None:
        self.cutscene_asset_path = cutscene_path
        super().__init__(project_path=project_path)
        self.cutscene_project_path = self.project_path
        self.cutscene_project_context = self.project_context

    def editor_asset_reference(self) -> str | Path | None:
        return self.cutscene_asset_path

    def create_editor_scene(self) -> CutsceneEditorScene:
        return CutsceneEditorScene(
            self,
            self.project_path,
            self.cutscene_asset_path,
            self.project_context,
        )


def run_cutscene_editor(project_path: str | Path | None = None, cutscene_path: str | Path | None = None) -> int:
    return run_standalone_editor(
        CutsceneEditorApp,
        project_path=project_path,
        cutscene_path=cutscene_path,
    )


__all__ = ["CutsceneEditorApp", "CutsceneEditorScene", "run_cutscene_editor"]
