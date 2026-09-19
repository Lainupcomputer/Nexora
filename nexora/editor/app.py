from __future__ import annotations

from pathlib import Path

from nexora import Game

from nexora.editor.scene import (
    EditorScene,
)
from nexora.editor.model import (
    EditorDocument,
    ProjectModel,
    SelectionService,
)


def resolve_project_path(
    project_path: str | Path | None,
) -> Path:
    """
    Resolve the project directory opened by the editor.

    ``None`` and ``"."`` both resolve to the current working
    directory. The path must exist and be a directory.
    """

    raw = (
        Path.cwd()
        if project_path is None
        else Path(
            project_path
        ).expanduser()
    )

    resolved = raw.resolve()

    if not resolved.exists():
        raise FileNotFoundError(
            f"Editor project path does not exist: "
            f"{resolved}"
        )

    if not resolved.is_dir():
        raise NotADirectoryError(
            f"Editor project path is not a directory: "
            f"{resolved}"
        )

    return resolved


class EditorApp(Game):
    """
    Nexora Editor application.

    The editor intentionally runs on Nexora itself. That keeps the
    editor on the same rendering, input, UI and scene stack as games
    built with the engine.
    """

    def __init__(
        self,
        *,
        project_path: str | Path | None = None,
    ) -> None:
        self.editor_project_path = (
            resolve_project_path(
                project_path
            )
        )

        super().__init__(
            project_name="NexoraEditor",
            title=(
                "Nexora Editor - "
                f"{self.editor_project_path.name}"
            ),
            width=1440,
            height=900,
            resizable=True,
            editor_mode=True,
        )

        self.editor_scene = None
        self._play_scene = None
        self._play_mode = False

    def initialize(
        self,
    ) -> None:
        icon_path = self.editor_project_path / "assets" / "icon.png"
        if self.window is not None and icon_path.is_file():
            try:
                self.window.set_icon(icon_path)
            except Exception:
                pass

        self.editor_project = ProjectModel(
            self.editor_project_path
        )

        self.editor_document = EditorDocument()
        self.editor_selection = SelectionService()

        self.editor_scene = EditorScene(
            self,
            self.editor_project_path,
            project=self.editor_project,
            document=self.editor_document,
            selection=self.editor_selection,
        )
        self.scene = self.editor_scene

    @property
    def play_mode(self) -> bool:
        return self._play_mode

    def _play_serialization_context(self) -> dict:
        context = {
            "game": self,
            "engine": self.engine,
            "renderer": self.renderer,
            "input": self.input,
        }
        if self.engine is not None:
            context["assets"] = self.engine.assets
            context["audio"] = self.engine.audio
        return context

    def _play_scene_name(self, original_name: str) -> str:
        name = str(original_name).strip() or "Scene"
        if self.scenes.get(name) is None:
            return name

        base = f"{name} (Play)"
        candidate = base
        index = 2
        while self.scenes.get(candidate) is not None:
            candidate = f"{base} {index}"
            index += 1
        return candidate

    def start_play_mode(self) -> None:
        if self._play_mode or self.editor_scene is None:
            return

        document = self.editor_document
        serializer = self.scene_serializer
        base_dir = (
            document.path.parent
            if document.path is not None
            else self.editor_project_path
        )
        runtime_scene = None

        self.editor_scene._sync_all_prefab_instance_overrides()

        try:
            runtime_scene = serializer.from_state(
                serializer.to_state(document.scene),
                base_dir=base_dir,
                context=self._play_serialization_context(),
            )
            runtime_scene.name = self._play_scene_name(runtime_scene.name)
            self._play_scene = runtime_scene
            self._play_mode = True
            self.scenes.load(runtime_scene, activate=True)
        except Exception as exc:
            self._play_mode = False
            self._play_scene = None
            if runtime_scene is not None:
                loaded = self.scenes.get(runtime_scene.name)
                if loaded is runtime_scene:
                    try:
                        self.scenes.unload(runtime_scene.name)
                    except Exception:
                        pass
                elif not runtime_scene.destroyed:
                    runtime_scene.destroy()
            self.editor_scene._show_error(
                f"Could not start play mode:\n{exc}"
            )
            return

        self.editor_scene.play_button.text = "Stop"

    def stop_play_mode(self) -> None:
        if not self._play_mode:
            return

        editor_scene = self.editor_scene

        try:
            if editor_scene is not None:
                self.scenes.change_scene(
                    editor_scene.name,
                    unload_previous=True,
                )
        except Exception as exc:
            if editor_scene is not None:
                editor_scene._show_error(
                    f"Could not stop play mode:\n{exc}"
                )
            return

        self._play_mode = False
        self._play_scene = None

        if editor_scene is not None:
            editor_scene.play_button.text = "Run"
            editor_scene.status_label.text = "Play mode stopped"
            editor_scene._refresh_document_ui()

    def update(self, delta_time: float) -> None:
        if self._play_mode and self.input is not None:
            if self.input.key_pressed("f8"):
                self.stop_play_mode()
                return

        super().update(delta_time)


def run_editor(
    project_path: str | Path | None = None,
) -> int:
    try:
        app = EditorApp(
            project_path=project_path,
        )

    except (
        FileNotFoundError,
        NotADirectoryError,
    ) as exc:
        print(
            f"[Nexora Editor] {exc}"
        )

        return 2

    app.run()
    return 0
