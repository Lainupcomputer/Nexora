from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys

from nexora.nodes.ui.containers.panel import Panel


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".webp",
}

AUDIO_EXTENSIONS = {
    ".wav",
    ".ogg",
    ".mp3",
    ".flac",
}

SCENE_EXTENSIONS = {
    ".nxscene",
}

PREFAB_EXTENSIONS = {
    ".nxprefab",
}

FONT_EXTENSIONS = {
    ".ttf",
    ".otf",
}

SHADER_EXTENSIONS = {
    ".hlsl",
    ".glsl",
    ".vert",
    ".frag",
    ".spv",
}

SCRIPT_EXTENSIONS = {
    ".py",
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
}


@dataclass(frozen=True, slots=True)
class AssetEntry:
    path: Path
    relative_path: Path
    name: str
    kind: str
    is_directory: bool
    extension: str
    size_bytes: int

    @property
    def display_name(self) -> str:
        if self.is_directory:
            return f"[DIR]  {self.name}"

        icon = {
            "scene": "[SCN]",
            "prefab": "[PFB]",
            "image": "[IMG]",
            "audio": "[AUD]",
            "font": "[FNT]",
            "shader": "[SHD]",
            "script": "[PY ]",
            "text": "[TXT]",
        }.get(
            self.kind,
            "[FILE]",
        )

        return f"{icon}  {self.name}"

    @property
    def drag_payload(self) -> AssetDragPayload:
        return AssetDragPayload(
            path=self.path,
            relative_path=self.relative_path,
            kind=self.kind,
        )


@dataclass(frozen=True, slots=True)
class AssetDragPayload:
    """Editor-side payload prepared for future drag/drop consumers."""

    path: Path
    relative_path: Path
    kind: str


def classify_asset(path: Path) -> str:
    if path.is_dir():
        return "folder"

    suffix = path.suffix.lower()

    if suffix in SCENE_EXTENSIONS:
        return "scene"

    if suffix in PREFAB_EXTENSIONS:
        return "prefab"

    if suffix in IMAGE_EXTENSIONS:
        return "image"

    if suffix in AUDIO_EXTENSIONS:
        return "audio"

    if suffix in FONT_EXTENSIONS:
        return "font"

    if suffix in SHADER_EXTENSIONS:
        return "shader"

    if suffix in SCRIPT_EXTENSIONS:
        return "script"

    if suffix in TEXT_EXTENSIONS:
        return "text"

    return "file"


def format_file_size(size: int) -> str:
    value = float(max(0, int(size)))

    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"

            return f"{value:.1f} {unit}"

        value /= 1024.0

    return f"{value:.1f} GB"


class AssetBrowserModel:
    """Safe project-local filesystem model used by the editor Asset dock."""

    DEFAULT_IGNORED_NAMES = {
        ".git",
        ".github",
        ".idea",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "Bruch",
        "__pycache__",
        "build",
        "dist",
        "env",
        "htmlcov",
        "venv",
    }

    def __init__(
        self,
        root_path: Path,
    ) -> None:
        self.root_path = Path(
            root_path
        ).resolve()

        self.current_path = (
            self.root_path
        )

        self.search_text = ""

        self.entries: list[
            AssetEntry
        ] = []

        self.refresh()

    def _resolve_inside_root(
        self,
        path: Path,
    ) -> Path:
        path = Path(
            path
        )

        if not path.is_absolute():
            path = (
                self.current_path
                / path
            )

        resolved = path.resolve()

        try:
            resolved.relative_to(
                self.root_path
            )

        except ValueError as exc:
            raise ValueError(
                "Asset path escapes the project root."
            ) from exc

        return resolved

    @property
    def relative_directory(self) -> Path:
        relative = (
            self.current_path
            .relative_to(
                self.root_path
            )
        )

        if str(relative) == ".":
            return Path(".")

        return relative

    @property
    def can_go_up(self) -> bool:
        return (
            self.current_path
            != self.root_path
        )

    def set_search(
        self,
        text: str,
    ) -> None:
        self.search_text = (
            str(text)
            .strip()
            .lower()
        )

        self.refresh()

    def navigate(
        self,
        path: Path,
    ) -> None:
        resolved = (
            self._resolve_inside_root(
                path
            )
        )

        if not resolved.is_dir():
            raise NotADirectoryError(
                resolved
            )

        self.current_path = (
            resolved
        )

        self.refresh()

    def go_up(
        self,
    ) -> None:
        if not self.can_go_up:
            return

        self.navigate(
            self.current_path.parent
        )

    def _include_path(
        self,
        path: Path,
    ) -> bool:
        if (
            path.name
            in self.DEFAULT_IGNORED_NAMES
        ):
            return False

        if not self.search_text:
            return True

        return (
            self.search_text
            in path.name.lower()
        )

    def _entry_for(
        self,
        path: Path,
    ) -> AssetEntry:
        is_directory = (
            path.is_dir()
        )

        try:
            size = (
                0
                if is_directory
                else path.stat().st_size
            )

        except OSError:
            size = 0

        return AssetEntry(
            path=path,
            relative_path=(
                path.relative_to(
                    self.root_path
                )
            ),
            name=path.name,
            kind=classify_asset(
                path
            ),
            is_directory=is_directory,
            extension=(
                ""
                if is_directory
                else path.suffix.lower()
            ),
            size_bytes=int(
                size
            ),
        )

    def refresh(
        self,
    ) -> list[AssetEntry]:
        if not self.current_path.is_dir():
            self.current_path = (
                self.root_path
            )

        entries: list[
            AssetEntry
        ] = []

        try:
            children = list(
                self.current_path.iterdir()
            )

        except OSError:
            children = []

        for path in children:
            if not self._include_path(
                path
            ):
                continue

            entries.append(
                self._entry_for(
                    path
                )
            )

        entries.sort(
            key=lambda entry: (
                not entry.is_directory,
                entry.name.lower(),
            )
        )

        self.entries = entries

        return list(
            entries
        )

    def entry_at(
        self,
        index: int,
    ) -> AssetEntry | None:
        if not (
            0
            <= int(index)
            < len(self.entries)
        ):
            return None

        return self.entries[
            int(index)
        ]


def reveal_in_file_manager(
    path: Path,
) -> None:
    path = Path(
        path
    ).resolve()

    target = (
        path
        if path.is_dir()
        else path.parent
    )

    if sys.platform.startswith(
        "win"
    ):
        os.startfile(
            str(target)
        )
        return

    if sys.platform == "darwin":
        subprocess.Popen(
            [
                "open",
                str(target),
            ]
        )
        return

    subprocess.Popen(
        [
            "xdg-open",
            str(target),
        ]
    )


class AssetPreview(Panel):
    """Small selected-image thumbnail rendered by the Nexora AssetManager."""

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.asset_manager = None
        self.asset_path: (
            Path | None
        ) = None

        self._texture = None
        self._loaded_path: (
            Path | None
        ) = None
        self._load_error: (
            str | None
        ) = None

        self.background = (
            20,
            22,
            25,
            255,
        )

        self.border_color = (
            60,
            64,
            70,
            255,
        )

        self.border_width = 1.0
        self.border_radius = 4.0

    @property
    def load_error(
        self,
    ) -> str | None:
        return self._load_error

    def set_asset(
        self,
        path: Path | None,
    ) -> None:
        normalized = (
            None
            if path is None
            else Path(path).resolve()
        )

        if normalized == self.asset_path:
            return

        self.asset_path = (
            normalized
        )

        self._texture = None
        self._loaded_path = None
        self._load_error = None

    def _ensure_texture(
        self,
    ) -> None:
        path = self.asset_path

        if (
            path is None
            or self.asset_manager is None
        ):
            return

        if self._loaded_path == path:
            return

        self._loaded_path = path
        self._texture = None
        self._load_error = None

        try:
            self._texture = (
                self.asset_manager.texture(
                    path
                )
            )

        except Exception as exc:
            self._load_error = str(
                exc
            )

    def render(
        self,
        renderer,
    ) -> None:
        if not self.visible:
            return

        super().render(
            renderer
        )

        self._ensure_texture()

        texture = self._texture

        if texture is None:
            return

        width = float(
            texture.width
        )
        height = float(
            texture.height
        )

        if (
            width <= 0.0
            or height <= 0.0
        ):
            return

        box_w = max(
            1.0,
            float(self.size[0])
            - 16.0,
        )

        box_h = max(
            1.0,
            float(self.size[1])
            - 16.0,
        )

        scale = min(
            box_w / width,
            box_h / height,
            1.0,
        )

        draw_w = max(
            1.0,
            width * scale,
        )

        draw_h = max(
            1.0,
            height * scale,
        )

        x, y = (
            self.calculate_position()
        )

        renderer.sprite(
            texture,
            x,
            y,
            width=draw_w,
            height=draw_h,
        )
