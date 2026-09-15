from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Sequence


class AssetCategory(str, Enum):
    """Ordered asset categories used by Nexora loading screens."""

    FONT = "Font"
    AUDIO = "Audio"
    TEXTURE = "Texture"


@dataclass(slots=True, frozen=True)
class FontAssetRequest:
    path: str | Path
    size: float


@dataclass(slots=True, frozen=True)
class AssetLoadProgress:
    """Progress snapshot emitted while assets are initialized."""

    category: AssetCategory
    current: int
    total: int
    progress: float
    asset_path: str | None = None

    @property
    def percent(self) -> int:
        return int(round(max(0.0, min(1.0, self.progress)) * 100.0))

    @property
    def status(self) -> str:
        return f"Initialisiere Assets: {self.category.value} {self.percent}%"


@dataclass(slots=True)
class AssetLoadCallbacks:
    """Optional callbacks shared by synchronous and scene-based loading."""

    on_stage_started: Callable[[AssetLoadProgress], None] | None = None
    on_progress: Callable[[AssetLoadProgress], None] | None = None
    on_asset_loaded: Callable[[AssetLoadProgress], None] | None = None
    on_completed: Callable[[], None] | None = None
    on_failed: Callable[[BaseException], None] | None = None


def normalize_font_requests(
    fonts: Iterable[FontAssetRequest | tuple[str | Path, float]],
) -> list[FontAssetRequest]:
    result: list[FontAssetRequest] = []

    for item in fonts:
        if isinstance(item, FontAssetRequest):
            request = item
        else:
            try:
                path, size = item
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    "Font assets must be FontAssetRequest or (path, size) pairs."
                ) from exc
            request = FontAssetRequest(path=path, size=float(size))

        if float(request.size) <= 0.0:
            raise ValueError("Font size must be greater than zero.")

        result.append(request)

    return result
