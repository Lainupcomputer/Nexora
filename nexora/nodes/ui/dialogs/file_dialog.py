from __future__ import annotations

from pathlib import Path

from nexora.nodes.ui.dialogs.dialog import Dialog
from nexora.nodes.ui.containers.list_view import ListView
from nexora.nodes.ui.controls.text_input import TextInput
from nexora.nodes.ui.output.label import Label
from nexora.signals import Signal


class FileDialog(Dialog):
    """Simple project-friendly file browser dialog.

    ``mode`` is either ``"open"`` or ``"save"``.  The browser can be
    constrained to a root directory, which is useful for editor project
    files and prevents accidental navigation outside the project.
    """

    VALID_MODES = ("open", "save")

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.dialog_size = (760.0, 520.0)
        self.mode: str = "open"
        self.root_path = Path.cwd().resolve()
        self.current_path = self.root_path
        self.extensions: tuple[str, ...] = ()
        self.selected_path: Path | None = None
        self.allow_directories: bool = False

        self.file_selected = Signal(f"{name}.file_selected", owner=self)

        self.path_label = self.content.create_child("Path", node_type=Label)
        self.path_label.anchor = (0.0, 0.0)
        self.path_label.pivot = (0.0, 0.0)
        self.path_label.scale = 0.78

        self.file_list = self.content.create_child("Files", node_type=ListView)
        self.file_list.item_height = 34.0
        self.file_list.padding_left = 6.0
        self.file_list.padding_right = 6.0
        self.file_list.padding_top = 6.0
        self.file_list.padding_bottom = 6.0
        self.file_list.text_scale = 0.82
        self.file_list.on_change = self._on_list_change
        self.file_list.on_activate = self._on_list_activate

        self.filename_input = self.content.create_child("Filename", node_type=TextInput)
        self.filename_input.placeholder = "File name"
        self.filename_input.on_submit = lambda _text: self.confirm()

        self._entries: list[Path] = []
        self._refresh_entries()

    def configure(
        self,
        *,
        mode: str = "open",
        root_path: str | Path | None = None,
        current_path: str | Path | None = None,
        extensions: tuple[str, ...] | list[str] = (),
        title: str | None = None,
    ) -> FileDialog:
        mode = str(mode).lower()
        if mode not in self.VALID_MODES:
            raise ValueError("FileDialog mode must be 'open' or 'save'.")
        self.mode = mode

        if root_path is not None:
            self.root_path = Path(root_path).expanduser().resolve()
        if current_path is None:
            self.current_path = self.root_path
        else:
            candidate = Path(current_path).expanduser().resolve()
            self.current_path = candidate if self._inside_root(candidate) else self.root_path

        normalized: list[str] = []
        for ext in extensions:
            ext = str(ext).lower().strip()
            if ext and not ext.startswith("."):
                ext = "." + ext
            if ext:
                normalized.append(ext)
        self.extensions = tuple(normalized)

        self.title = title or ("Open File" if mode == "open" else "Save File")
        self.confirm_text = "Open" if mode == "open" else "Save"
        self.selected_path = None
        self.filename_input.set_text("", emit=False)
        self._refresh_entries()
        return self

    def _inside_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root_path.resolve())
            return True
        except ValueError:
            return False

    def _matches_extension(self, path: Path) -> bool:
        if not self.extensions:
            return True
        return path.suffix.lower() in self.extensions

    def _refresh_entries(self) -> None:
        try:
            entries = list(self.current_path.iterdir())
        except (OSError, FileNotFoundError):
            entries = []

        directories = sorted(
            (entry for entry in entries if entry.is_dir()),
            key=lambda item: item.name.lower(),
        )
        files = sorted(
            (entry for entry in entries if entry.is_file() and self._matches_extension(entry)),
            key=lambda item: item.name.lower(),
        )

        self._entries = []
        labels: list[str] = []
        if self.current_path != self.root_path and self._inside_root(self.current_path.parent):
            self._entries.append(self.current_path.parent)
            labels.append("[..]")

        for directory in directories:
            self._entries.append(directory)
            labels.append(f"[{directory.name}]")
        for file in files:
            self._entries.append(file)
            labels.append(file.name)

        self.file_list.set_items(labels)
        self.path_label.text = str(self.current_path)

    def _on_list_change(self, index: int, _item: str | None) -> None:
        if not (0 <= index < len(self._entries)):
            return
        path = self._entries[index]
        if path.is_file():
            self.selected_path = path
            self.filename_input.set_text(path.name, emit=False)

    def _on_list_activate(self, index: int, _item: str) -> None:
        if not (0 <= index < len(self._entries)):
            return
        path = self._entries[index]
        if path.is_dir():
            if self._inside_root(path):
                self.current_path = path.resolve()
                self.selected_path = None
                self._refresh_entries()
            return
        self.selected_path = path
        self.filename_input.set_text(path.name, emit=False)
        if self.mode == "open":
            self.confirm()

    def _candidate_path(self) -> Path | None:
        text = self.filename_input.text.strip()
        if text:
            candidate = (self.current_path / text).resolve()
        else:
            candidate = self.selected_path
        if candidate is None or not self._inside_root(candidate):
            return None
        return candidate

    def confirm(self) -> None:
        if not self.is_open:
            return

        candidate = self._candidate_path()
        if candidate is None:
            return

        if self.mode == "open":
            if candidate.is_dir() and not self.allow_directories:
                self.current_path = candidate
                self._refresh_entries()
                return
            if not candidate.exists():
                return
            if candidate.is_file() and not self._matches_extension(candidate):
                return
        else:
            if candidate.exists() and candidate.is_dir():
                self.current_path = candidate
                self._refresh_entries()
                return
            if self.extensions and candidate.suffix == "":
                candidate = candidate.with_suffix(self.extensions[0])
            if not self._inside_root(candidate):
                return

        self.selected_path = candidate
        self.file_selected.emit(self, candidate)
        super().confirm()

    def _sync_layout(self) -> None:
        super()._sync_layout()
        width, height = self.content.size
        path_h = 28.0
        input_h = 44.0
        gap = 10.0

        self.path_label.position = (-width / 2.0, -height / 2.0)

        self.file_list.anchor = (0.5, 0.5)
        self.file_list.pivot = (0.5, 0.5)
        self.file_list.size = (width, max(0.0, height - path_h - input_h - gap * 2.0))
        self.file_list.position = (0.0, (path_h - input_h) / 2.0)

        self.filename_input.anchor = (0.5, 1.0)
        self.filename_input.pivot = (0.5, 0.5)
        self.filename_input.size = (width, input_h)
        self.filename_input.position = (0.0, -input_h / 2.0)

    def open(self, *, focus=None) -> FileDialog:
        self._refresh_entries()
        return super().open(focus=focus or self.file_list)
