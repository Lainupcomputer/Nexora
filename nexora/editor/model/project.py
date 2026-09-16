from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
