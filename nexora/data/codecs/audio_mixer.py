from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data import DataFile, DataType, load_file, save_file

VERSION = 1


def encode(snapshot: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise TypeError("Mixer snapshot must be a dictionary.")
    return dict(snapshot)


def decode(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ValueError("Invalid Nexora audio mixer data.")
    return dict(state)


def save(snapshot: dict[str, Any], path: str | Path) -> Path:
    return save_file(
        path,
        DataFile(DataType.AudioMixer, VERSION, encode(snapshot)),
    )


def load(path: str | Path) -> dict[str, Any]:
    document = load_file(path, expected_type=DataType.AudioMixer)
    if document.version != VERSION:
        raise ValueError(
            f"Unsupported Nexora audio mixer data version: {document.version}"
        )
    return decode(document.data)


__all__ = ["VERSION", "decode", "encode", "load", "save"]
