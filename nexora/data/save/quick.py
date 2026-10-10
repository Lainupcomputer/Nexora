from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nexora.data.save.events import SaveKind
from nexora.data.save.save_data import SaveGame, SaveMetadata


class QuickSaveController:
    """Quick-save policy separated from the general save manager."""

    def __init__(
        self,
        *,
        enabled: bool,
        slot: str,
        validate_slot: Callable[[str], str],
        save: Callable[..., SaveMetadata],
        load: Callable[..., SaveGame],
        exists: Callable[[str], bool],
        delete: Callable[..., bool],
    ) -> None:
        self._validate_slot = validate_slot
        self._save = save
        self._load = load
        self._exists = exists
        self._delete = delete
        self.enabled = bool(enabled)
        self.slot = slot

    @property
    def slot(self) -> str:
        return self._slot

    @slot.setter
    def slot(self, value: str) -> None:
        self._slot = self._validate_slot(value)

    def save(
        self,
        data: dict[str, Any],
        *,
        name: str = "Quick Save",
        playtime: float = 0.0,
    ) -> SaveMetadata:
        if not self.enabled:
            raise RuntimeError("Quick saving is disabled.")
        return self._save(
            self.slot,
            data,
            name=name,
            playtime=playtime,
            kind=SaveKind.QUICK,
        )

    def load(self) -> SaveGame:
        if not self.enabled:
            raise RuntimeError("Quick saving is disabled.")
        return self._load(self.slot, kind=SaveKind.QUICK)

    def exists(self) -> bool:
        if not self.enabled:
            return False
        return self._exists(self.slot)

    def delete(self) -> bool:
        return self._delete(self.slot, kind=SaveKind.QUICK)
