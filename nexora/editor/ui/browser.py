"""Shared filesystem browser state for standalone editor dialogs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


DEFAULT_HIDDEN_DIRECTORIES = frozenset(
    {".git", ".venv", "__pycache__", "build", "dist", "Bruch", "MyGame"}
)


class FileBrowserModel:
    """Project-scoped directory browser used by all standalone editors.

    The model owns navigation, filtering and the display order.  Editors only
    decide what a selected file means (open, save, icon, image or audio), so
    that platform-specific ``[..]`` handling is implemented once.
    """

    def __init__(self, *, hidden_directories: Iterable[str] = DEFAULT_HIDDEN_DIRECTORIES) -> None:
        self.hidden_directories = frozenset(str(name) for name in hidden_directories)
        self.root = Path.cwd().resolve()
        self.path = self.root
        self.extensions: tuple[str, ...] = ()
        self.entries: list[Path] = []
        self.labels: list[str] = []

    def open(
        self,
        root: str | Path,
        *,
        start: str | Path | None = None,
        extensions: Iterable[str] = (),
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        requested_path = Path(start).expanduser() if start is not None else self.root
        self.path = self._confine(requested_path)
        self.extensions = tuple(str(extension).lower() for extension in extensions)
        self.refresh()

    def refresh(self) -> tuple[str, ...]:
        try:
            entries = list(self.path.iterdir())
        except (FileNotFoundError, OSError):
            entries = []

        directories = sorted(
            (
                entry
                for entry in entries
                if entry.is_dir() and entry.name not in self.hidden_directories
            ),
            key=lambda entry: entry.name.lower(),
        )
        files = sorted(
            (
                entry
                for entry in entries
                if entry.is_file() and self._matches_extension(entry)
            ),
            key=lambda entry: entry.name.lower(),
        )

        self.entries = []
        self.labels = []
        if self.path != self.root:
            self.entries.append(self.path.parent)
            self.labels.append("[..]")
        self.entries.extend(directories)
        self.labels.extend(f"[{entry.name}]" for entry in directories)
        self.entries.extend(files)
        self.labels.extend(entry.name for entry in files)
        return tuple(self.labels)

    def select(self, index: int) -> Path | None:
        """Navigate or return the selected file.

        ``None`` means the selection was navigation or invalid.  A returned
        path is always a file currently visible in the browser.
        """

        if not 0 <= int(index) < len(self.entries):
            return None
        path = self.entries[int(index)]
        if self.path != self.root and int(index) == 0:
            self.go_up()
            return None
        if path.is_dir():
            self.path = self._confine(path)
            self.refresh()
            return None
        return path.resolve()

    def go_up(self) -> bool:
        if self.path == self.root:
            return False
        self.path = self._confine(self.path.parent)
        self.refresh()
        return True

    def _matches_extension(self, path: Path) -> bool:
        if not self.extensions:
            return True
        name = path.name.lower()
        return any(name.endswith(extension) for extension in self.extensions)

    def _confine(self, path: Path) -> Path:
        candidate = path.resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            return self.root
        return candidate


def sync_browser_list(browser: FileBrowserModel, list_box) -> None:
    """Copy browser labels into the shared renderer-backed list widget."""

    list_box.set_items(browser.labels)
    list_box.selected = -1
