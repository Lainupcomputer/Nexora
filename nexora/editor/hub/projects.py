from __future__ import annotations

from pathlib import Path
import subprocess

from nexora.cli.project import generate_project
from nexora.editor.hub.project_wizard import NewProjectRequest
from nexora.editor.hub.recent_projects import forget_project, load_recent_projects, remember_project
from nexora.editor.main.app import resolve_project_path
from nexora.editor.model import EditorProjectContext


class HubProjectsMixin:
    """Project selection, recent projects, and project creation workflows."""

    def _remember_current_project(self) -> None:
        self._recent_projects = remember_project(self.project_path)
        self._refresh_recent_projects()

    def _refresh_recent_projects(self) -> None:
        self._recent_projects = load_recent_projects()
        self._recent_entries = list(self._recent_projects)
        self._recent_selected_index = -1
        labels = []
        for path in self._recent_entries:
            marker = "  [current]" if path == self.project_path else ""
            labels.append(f"{path.name}{marker}\n{path}")
        self.recent_list.set_items(labels)

    def _sync_project_display(self) -> None:
        self.project_name.text = self.project_path.name
        self.project_path_label.text = str(self.project_path)
        title = f"Nexora Project Hub - {self.project_path.name}"
        window = getattr(self.game, "window", None)
        if window is not None:
            try:
                window.set_title(title)
            except Exception:
                pass

    def _open_new_project_wizard(self) -> None:
        self.new_project_wizard.name_input.set_text("MyGame", emit=False)
        self.new_project_wizard.set_location(Path.home())
        self.new_project_wizard.open()
        self.status_label.text = "Creating a new project"

    def _browse_new_project_location(self) -> None:
        home = Path.home().resolve()
        text = self.new_project_wizard.location_input.text.strip()
        current = Path(text).expanduser() if text else home
        try:
            current = current.resolve()
            current.relative_to(home)
        except (OSError, ValueError):
            current = home
        if not current.is_dir():
            current = home

        self.new_project_location_dialog.configure(
            mode="open",
            root_path=home,
            current_path=current,
            title="Choose Project Location",
            directories_only=True,
        )
        self.new_project_location_dialog.allow_directories = True
        self.new_project_location_dialog.confirm_text = "Select Folder"
        self.new_project_location_dialog.open()

    def _on_new_project_location_selected(self, _dialog, path: Path) -> None:
        self.new_project_wizard.set_location(path)

    def _create_new_project(self, request: NewProjectRequest) -> bool:
        try:
            project = generate_project(request.name, request.parent)
        except (ValueError, FileExistsError, NotADirectoryError, OSError) as exc:
            self.new_project_wizard.show_error(str(exc))
            return False

        if request.initialize_git:
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=str(project.root),
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                self.status_label.text = f"Project created, but Git init failed: {exc}"

        self._set_project(project.root)
        self.status_label.text = f"Created project: {project.root.name}"

        if request.open_main_editor:
            self._open_editor("--editor")

        return True

    def _open_project_dialog(self) -> None:
        home = Path.home().resolve()
        current = self.project_path
        try:
            current.relative_to(home)
        except ValueError:
            current = home

        self.project_dialog.configure(
            mode="open",
            root_path=home,
            current_path=current,
            title="Open Nexora Project",
            directories_only=True,
        )
        self.project_dialog.allow_directories = True
        self.project_dialog.confirm_text = "Open Project"
        self.project_dialog.open()

    def _on_project_selected(self, _dialog, path: Path) -> None:
        self._set_project(path)

    def _set_project(self, path: str | Path) -> None:
        try:
            project_path = resolve_project_path(path)
            context = EditorProjectContext.from_path(project_path)
        except (FileNotFoundError, NotADirectoryError) as exc:
            self.status_label.text = str(exc)
            return

        self.project_path = project_path
        self.project_context = context
        self._recent_projects = remember_project(project_path)
        self._sync_project_display()
        self._refresh_recent_projects()
        self.status_label.text = f"Selected project: {project_path.name}"

    def _on_recent_selected(self, index: int, _text: str | None) -> None:
        if 0 <= index < len(self._recent_entries):
            self._recent_selected_index = index
            self.status_label.text = str(self._recent_entries[index])
            return
        self._recent_selected_index = -1

    def _on_recent_activated(self, index: int, _text: str) -> None:
        if 0 <= index < len(self._recent_entries):
            self._set_project(self._recent_entries[index])

    def _selected_recent_project(self) -> Path | None:
        index = self._recent_selected_index
        if 0 <= index < len(self._recent_entries):
            return self._recent_entries[index]
        return None

    def _open_selected_recent(self) -> None:
        path = self._selected_recent_project()
        if path is None:
            self.status_label.text = "Select a recent project first"
            return
        self._set_project(path)

    def _remove_selected_recent(self) -> None:
        path = self._selected_recent_project()
        if path is None:
            self.status_label.text = "Select a recent project first"
            return
        forget_project(path)
        self._refresh_recent_projects()
        self.status_label.text = f"Removed from recent projects: {path.name}"
