from __future__ import annotations

from typing import Any

from nexora.data import DataFile, DataType, decode_file, encode_file
from nexora.data.errors import DataIntegrityError, DataError

from .errors import InvalidSceneFileError, SceneIntegrityError

# Kept as API selectors only. Files now use the shared NXDATA01 container.
SCENE_MAGIC = b"NXSCN001"
PREFAB_MAGIC = b"NXPFB001"


def _data_type_for_magic(magic: bytes) -> DataType:
    if magic == SCENE_MAGIC:
        return DataType.Scene
    if magic == PREFAB_MAGIC:
        return DataType.Prefab
    raise ValueError("Unknown Nexora scene serialization selector.")


def encode_secure_pickle(
    value: Any,
    *,
    signing_key: bytes | str,
    magic: bytes,
) -> bytes:
    data_type = _data_type_for_magic(magic)
    version = int(value.get("schema_version", 1)) if isinstance(value, dict) else 1
    return encode_file(
        DataFile(data_type=data_type, version=version, data=value),
        signing_key=signing_key,
    )


def decode_secure_pickle(
    raw: bytes,
    *,
    signing_key: bytes | str,
    expected_magic: bytes,
    max_payload_size: int,
) -> Any:
    try:
        return decode_file(
            raw,
            expected_type=_data_type_for_magic(expected_magic),
            signing_key=signing_key,
            max_payload_size=max_payload_size,
        ).data
    except DataIntegrityError as exc:
        raise SceneIntegrityError(str(exc)) from exc
    except DataError as exc:
        raise InvalidSceneFileError(str(exc)) from exc


__all__ = [
    "PREFAB_MAGIC",
    "SCENE_MAGIC",
    "decode_secure_pickle",
    "encode_secure_pickle",
]
