from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True, frozen=True)
class EditorProjectContext:
    """Canonical paths shared by every Nexora editor."""

    root: Path
    assets_root: Path
    items_root: Path
    cutscenes_root: Path
    scenes_root: Path
    prefabs_root: Path

    @classmethod
    def from_path(cls, root: str | Path) -> "EditorProjectContext":
        project_root = Path(root).expanduser().resolve()
        if not project_root.is_dir():
            raise NotADirectoryError(
                f"Project root is not a directory: {project_root}"
            )
        assets_root = next(
            (
                candidate
                for candidate in (
                    project_root / "assets",
                    project_root / "MyGame" / "assets",
                )
                if candidate.is_dir()
            ),
            project_root,
        )
        return cls(
            root=project_root,
            assets_root=assets_root,
            items_root=project_root / "items",
            cutscenes_root=project_root / "cutscenes",
            scenes_root=project_root / "scenes",
            prefabs_root=project_root / "prefabs",
        )

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def icon_path(self) -> Path:
        return self.assets_root / "icon.png"

    def asset_root_for(self, reference: str | Path | None = None) -> Path:
        """Return the asset root that belongs to a project-relative reference."""

        candidates: list[Path] = []
        if reference is not None:
            path = Path(reference).expanduser()
            if not path.is_absolute():
                path = self.root / path
            path = path.resolve()
            for parent in (path, *path.parents):
                if parent.name.lower() == "mygame":
                    candidates.append(parent / "assets")
                    break
        candidates.extend((self.root / "assets", self.root / "MyGame" / "assets"))
        return next((candidate for candidate in candidates if candidate.is_dir()), self.root)

    def relative_asset(self, path: str | Path, *, root: str | Path | None = None) -> str:
        candidate = Path(path).expanduser().resolve()
        asset_root = Path(root).resolve() if root is not None else self.assets_root.resolve()
        try:
            return candidate.relative_to(asset_root).as_posix()
        except ValueError:
            try:
                return candidate.relative_to(self.root).as_posix()
            except ValueError:
                return candidate.name

    def resolve_asset(
        self,
        value: str | Path,
        *,
        reference: str | Path | None = None,
    ) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        asset_root = self.asset_root_for(reference)
        candidates = (
            asset_root / path,
            self.root / path,
            self.root / "assets" / path,
            self.root / "MyGame" / "assets" / path,
        )
        return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])

    def resolve_project_file(
        self,
        value: str | Path,
        *,
        roots: Iterable[str | Path] = (),
    ) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        candidates = tuple(Path(root) / path for root in roots) + (
            self.root / path,
            Path.cwd() / path,
        )
        return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


@dataclass(slots=True, frozen=True)
class ProjectEntry:
    path: Path
    relative_path: Path
    kind: str


class ProjectModel:
    """Read-only view of files that belong to the opened Nexora project."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

        if not self.root.is_dir():
            raise NotADirectoryError(
                f"Project root is not a directory: {self.root}"
            )

        self.context = EditorProjectContext.from_path(self.root)

    @property
    def name(self) -> str:
        return self.root.name

    def iter_scene_files(self) -> tuple[Path, ...]:
        return tuple(
            sorted(
                path
                for path in self.root.rglob("*.nxscene")
                if path.is_file()
            )
        )

    def iter_assets(self) -> tuple[ProjectEntry, ...]:
        assets_root = self.root / "assets"

        if not assets_root.is_dir():
            return ()

        entries: list[ProjectEntry] = []

        for path in sorted(assets_root.rglob("*")):
            if not path.is_file():
                continue

            entries.append(
                ProjectEntry(
                    path=path,
                    relative_path=path.relative_to(self.root),
                    kind=path.suffix.lower().lstrip(".") or "file",
                )
            )

        return tuple(entries)
