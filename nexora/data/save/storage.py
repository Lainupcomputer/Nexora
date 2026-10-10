from __future__ import annotations

import re
from pathlib import Path

from nexora.data import atomic_write


_SLOT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class SaveSlotStore:
    """Filesystem-only storage for save slots.

    This class deliberately knows nothing about signatures, save metadata,
    autosave semantics, or events. Those remain responsibilities of
    ``SaveManager``.
    """

    def __init__(
        self,
        save_path: str | Path,
        *,
        extension: str = ".nxs",
        create_directory: bool = True,
    ) -> None:
        self.extension = str(extension)
        self.create_directory = bool(create_directory)
        self._path = Path()
        self.set_path(save_path, create_directory=self.create_directory)

    @staticmethod
    def validate_slot(slot: str) -> str:
        slot = str(slot)
        if not _SLOT_PATTERN.fullmatch(slot):
            raise ValueError(
                "Invalid save slot name. "
                "Allowed: A-Z, a-z, 0-9, '_' and '-'. "
                "Maximum length: 64."
            )
        return slot

    @property
    def path(self) -> Path:
        return self._path

    def set_path(
        self,
        value: str | Path,
        *,
        create_directory: bool | None = None,
    ) -> Path:
        path = Path(value).expanduser()
        if create_directory is None:
            create_directory = self.create_directory
        if create_directory:
            path.mkdir(parents=True, exist_ok=True)
        if path.exists() and not path.is_dir():
            raise NotADirectoryError(str(path))
        self._path = path.resolve()
        return self._path

    def slot_path(self, slot: str) -> Path:
        slot = self.validate_slot(slot)
        return self._path / f"{slot}{self.extension}"

    def exists(self, slot: str) -> bool:
        return self.slot_path(slot).is_file()

    def read(self, slot: str) -> bytes:
        return self.slot_path(slot).read_bytes()

    def write(self, slot: str, data: bytes) -> None:
        atomic_write(self.slot_path(slot), data)

    def write_path(self, destination: Path, data: bytes) -> None:
        atomic_write(destination, data)

    def delete(self, slot: str) -> bool:
        path = self.slot_path(slot)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_slots(self) -> tuple[str, ...]:
        slots: list[str] = []
        for path in self._path.glob(f"*{self.extension}"):
            if not path.is_file():
                continue
            slot = path.stem
            try:
                self.validate_slot(slot)
            except ValueError:
                continue
            slots.append(slot)
        slots.sort()
        return tuple(slots)
