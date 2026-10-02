from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import DataType


@dataclass(slots=True)
class DataFile:
    """Decoded Nexora data document."""

    data_type: DataType
    version: int
    data: Any

    def __post_init__(self) -> None:
        if not isinstance(self.data_type, DataType):
            self.data_type = DataType(self.data_type)
        self.version = int(self.version)
        if self.version <= 0:
            raise ValueError("DataFile version must be greater than zero.")


__all__ = ["DataFile"]
