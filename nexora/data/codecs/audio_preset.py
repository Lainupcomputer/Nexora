from __future__ import annotations

from pathlib import Path
from typing import Any

from nexora.data import DataFile, DataType, load_file, save_file

VERSION = 1


def encode(preset) -> dict[str, Any]:
    state = preset.to_dict()
    if not isinstance(state, dict):
        raise TypeError("AudioPreset.to_dict() must return a dictionary.")
    return state


def decode(state: Any):
    from nexora.audio.preset import AudioPreset

    if not isinstance(state, dict):
        raise ValueError("Invalid Nexora audio preset data.")
    return AudioPreset.from_dict(dict(state))


def save(preset, path: str | Path) -> Path:
    return save_file(
        path,
        DataFile(DataType.AudioPreset, VERSION, encode(preset)),
    )


def load(path: str | Path):
    document = load_file(path, expected_type=DataType.AudioPreset)
    if document.version != VERSION:
        raise ValueError(
            f"Unsupported Nexora audio preset data version: {document.version}"
        )
    return decode(document.data)


__all__ = ["VERSION", "decode", "encode", "load", "save"]
