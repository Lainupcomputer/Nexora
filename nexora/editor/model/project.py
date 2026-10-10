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

    def normalize_asset_reference(self, value: str | Path) -> Path:
        """Normalize asset references to the path stored below an asset root.

        Editors may encounter ``foo.png``, ``assets/foo.png`` or
        ``MyGame/assets/foo.png``.  Prefix handling is centralized here so all
        editor modes interpret the same serialized reference identically.
        """

        path = Path(value).expanduser()
        if path.is_absolute():
            return path

        parts = path.parts
        lowered = tuple(part.lower() for part in parts)
        if len(parts) >= 3 and lowered[:2] == ("mygame", "assets"):
            return Path(*parts[2:])
        if len(parts) >= 2 and lowered[0] == "assets":
            return Path(*parts[1:])
        return path

    def relative_asset(self, path: str | Path, *, root: str | Path | None = None) -> str:
        candidate = Path(path).expanduser().resolve()
        asset_root = (
            Path(root).expanduser().resolve()
            if root is not None
            else self.assets_root.resolve()
        )
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
        path = self.normalize_asset_reference(value)
        if path.is_absolute():
            return path.resolve()

        asset_root = self.asset_root_for(reference)
        candidates = self._unique_candidates((
            asset_root / path,
            self.root / path,
            self.root / "assets" / path,
            self.root / "MyGame" / "assets" / path,
        ))
        return self._first_existing_file(candidates)

    def resolve_project_file(
        self,
        value: str | Path,
        *,
        roots: Iterable[str | Path] = (),
        include_assets: bool = False,
        reference: str | Path | None = None,
        include_cwd: bool = True,
    ) -> Path:
        """Resolve an editor file using one project-wide candidate order.

        Extra ``roots`` are searched first.  Callers can include asset roots
        without rebuilding their own candidate list.  Project root and, by
        default, the current working directory are the final fallbacks.
        """

        raw_path = Path(value).expanduser()
        if raw_path.is_absolute():
            return raw_path.resolve()

        candidates: list[Path] = [
            Path(root).expanduser() / raw_path
            for root in roots
        ]
        if include_assets:
            asset_path = self.normalize_asset_reference(raw_path)
            asset_root = self.asset_root_for(reference)
            candidates.extend((
                asset_root / asset_path,
                self.root / "assets" / asset_path,
                self.root / "MyGame" / "assets" / asset_path,
            ))
        candidates.append(self.root / raw_path)
        if include_cwd:
            candidates.append(Path.cwd() / raw_path)

        return self._first_existing_file(self._unique_candidates(candidates))

    @staticmethod
    def _unique_candidates(candidates: Iterable[str | Path]) -> tuple[Path, ...]:
        result: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = Path(candidate).expanduser().resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            result.append(resolved)
        return tuple(result)

    @staticmethod
    def _first_existing_file(candidates: Iterable[Path]) -> Path:
        paths = tuple(candidates)
        if not paths:
            raise ValueError("At least one path candidate is required.")
        return next((candidate for candidate in paths if candidate.is_file()), paths[0])



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
        assets_root = self.context.assets_root

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
