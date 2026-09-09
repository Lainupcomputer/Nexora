from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AssetStatus(Enum):
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"


@dataclass(slots=True)
class Asset:
    path: str
    value: Any = None
    status: AssetStatus = AssetStatus.LOADING
    error: BaseException | None = None

    @property
    def loaded(self) -> bool:
        return self.status is AssetStatus.LOADED

    @property
    def failed(self) -> bool:
        return self.status is AssetStatus.FAILED