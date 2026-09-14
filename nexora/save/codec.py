from __future__ import annotations

import hashlib
import hmac
import io
import pickle
import pickletools
import struct
from typing import Any

from nexora.save.errors import (
    InvalidSaveError,
    SaveIntegrityError,
    UnsafeSaveDataError,
    UnsupportedSaveVersionError,
)


# ==============================================================
# FORMAT
# ==============================================================

MAGIC = b"NXSAVE01"

CONTAINER_VERSION = 1

DIGEST_SIZE = 32

# 8 byte magic
# 2 byte version
# 8 byte payload length
# 32 byte HMAC SHA256
_HEADER_STRUCT = struct.Struct(
    ">8sHQ32s"
)

_HEADER_PREFIX_STRUCT = struct.Struct(
    ">8sHQ"
)


# ==============================================================
# LIMITS
# ==============================================================

DEFAULT_MAX_DEPTH = 64
DEFAULT_MAX_ITEMS = 1_000_000

DEFAULT_MAX_STRING_SIZE = (
    4 * 1024 * 1024
)

DEFAULT_MAX_BYTES_SIZE = (
    32 * 1024 * 1024
)


# ==============================================================
# SAFE DATA TYPES
# ==============================================================

_SAFE_SCALAR_TYPES = (
    type(None),
    bool,
    int,
    float,
    str,
    bytes,
)


# ==============================================================
# DANGEROUS PICKLE OPCODES
# ==============================================================

_FORBIDDEN_OPCODES = {
    "GLOBAL",
    "STACK_GLOBAL",
    "REDUCE",
    "BUILD",
    "OBJ",
    "INST",
    "NEWOBJ",
    "NEWOBJ_EX",
    "EXT1",
    "EXT2",
    "EXT4",
    "PERSID",
    "BINPERSID",
}


# ==============================================================
# RESTRICTED UNPICKLER
# ==============================================================


class RestrictedUnpickler(
    pickle.Unpickler
):
    """
    Pickle unpickler which refuses global object resolution.

    Nexora save files only allow primitive container types.
    """

    def find_class(
        self,
        module: str,
        name: str,
    ):
        raise pickle.UnpicklingError(
            "Global object loading is disabled "
            "for Nexora save files."
        )

    def persistent_load(
        self,
        pid,
    ):
        raise pickle.UnpicklingError(
            "Persistent pickle IDs are disabled "
            "for Nexora save files."
        )


# ==============================================================
# VALIDATION
# ==============================================================


def validate_save_value(
    value: Any,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_string_size: int = DEFAULT_MAX_STRING_SIZE,
    max_bytes_size: int = DEFAULT_MAX_BYTES_SIZE,
) -> None:
    """
    Validate that an object contains only safe save data.

    Supported:

        None
        bool
        int
        float
        str
        bytes
        list
        tuple
        dict

    Arbitrary Python objects are rejected.
    """

    item_count = 0

    stack: list[
        tuple[Any, int]
    ] = [
        (
            value,
            0,
        )
    ]

    while stack:
        current, depth = (
            stack.pop()
        )

        if depth > max_depth:
            raise UnsafeSaveDataError(
                "Save data exceeds maximum nesting depth."
            )

        item_count += 1

        if item_count > max_items:
            raise UnsafeSaveDataError(
                "Save data exceeds maximum item count."
            )

        # ------------------------------------------------------
        # Scalars
        # ------------------------------------------------------

        if isinstance(
            current,
            _SAFE_SCALAR_TYPES,
        ):
            if isinstance(
                current,
                str,
            ):
                if (
                    len(
                        current.encode(
                            "utf-8"
                        )
                    )
                    > max_string_size
                ):
                    raise UnsafeSaveDataError(
                        "Save string exceeds maximum size."
                    )

            elif isinstance(
                current,
                bytes,
            ):
                if (
                    len(current)
                    > max_bytes_size
                ):
                    raise UnsafeSaveDataError(
                        "Save bytes object exceeds maximum size."
                    )

            continue

        # ------------------------------------------------------
        # List
        # ------------------------------------------------------

        if isinstance(
            current,
            list,
        ):
            for item in current:
                stack.append(
                    (
                        item,
                        depth + 1,
                    )
                )

            continue

        # ------------------------------------------------------
        # Tuple
        # ------------------------------------------------------

        if isinstance(
            current,
            tuple,
        ):
            for item in current:
                stack.append(
                    (
                        item,
                        depth + 1,
                    )
                )

            continue

        # ------------------------------------------------------
        # Dictionary
        # ------------------------------------------------------

        if isinstance(
            current,
            dict,
        ):
            for key, item in current.items():
                stack.append(
                    (
                        key,
                        depth + 1,
                    )
                )

                stack.append(
                    (
                        item,
                        depth + 1,
                    )
                )

            continue

        # ------------------------------------------------------
        # Everything else is forbidden
        # ------------------------------------------------------

        raise UnsafeSaveDataError(
            "Unsupported save data type: "
            f"{type(current).__name__}"
        )


# ==============================================================
# PICKLE OPCODE VALIDATION
# ==============================================================


def validate_pickle_opcodes(
    payload: bytes,
) -> None:
    """
    Reject pickle instructions capable of constructing or
    importing arbitrary Python objects.
    """

    try:
        operations = (
            pickletools.genops(
                payload
            )
        )

        for opcode, argument, position in operations:
            if (
                opcode.name
                in _FORBIDDEN_OPCODES
            ):
                raise UnsafeSaveDataError(
                    "Unsafe pickle opcode "
                    f"'{opcode.name}' "
                    f"at byte {position}."
                )

    except UnsafeSaveDataError:
        raise

    except Exception as exc:
        raise InvalidSaveError(
            "Could not parse pickle payload."
        ) from exc


# ==============================================================
# RESTRICTED LOAD
# ==============================================================


def restricted_loads(
    payload: bytes,
):
    """
    Safely decode an already authenticated Nexora payload.
    """

    validate_pickle_opcodes(
        payload
    )

    try:
        value = (
            RestrictedUnpickler(
                io.BytesIO(
                    payload
                )
            ).load()
        )

    except (
        pickle.UnpicklingError,
        EOFError,
        ValueError,
        TypeError,
    ) as exc:
        raise InvalidSaveError(
            "Invalid pickle payload."
        ) from exc

    validate_save_value(
        value
    )

    return value


# ==============================================================
# KEY NORMALIZATION
# ==============================================================


def normalize_signing_key(
    key: bytes | str,
) -> bytes:
    if isinstance(
        key,
        str,
    ):
        key = key.encode(
            "utf-8"
        )

    if not isinstance(
        key,
        bytes,
    ):
        raise TypeError(
            "signing_key must be bytes or str."
        )

    if len(key) < 32:
        raise ValueError(
            "signing_key must contain at least 32 bytes."
        )

    return key


# ==============================================================
# ENCODE
# ==============================================================


def encode_save(
    value,
    *,
    signing_key: bytes | str,
) -> bytes:
    """
    Serialize and authenticate Nexora save data.
    """

    key = normalize_signing_key(
        signing_key
    )

    # ----------------------------------------------------------
    # Validate BEFORE pickle
    # ----------------------------------------------------------

    validate_save_value(
        value
    )

    # ----------------------------------------------------------
    # Pickle
    # ----------------------------------------------------------

    payload = pickle.dumps(
        value,
        protocol=pickle.HIGHEST_PROTOCOL,
    )

    # ----------------------------------------------------------
    # Ensure our own output also stays inside restricted format.
    # ----------------------------------------------------------

    validate_pickle_opcodes(
        payload
    )

    payload_length = len(
        payload
    )

    # ----------------------------------------------------------
    # Header material included in signature
    # ----------------------------------------------------------

    prefix = (
        _HEADER_PREFIX_STRUCT.pack(
            MAGIC,
            CONTAINER_VERSION,
            payload_length,
        )
    )

    digest = hmac.new(
        key,
        prefix + payload,
        hashlib.sha256,
    ).digest()

    return (
        _HEADER_STRUCT.pack(
            MAGIC,
            CONTAINER_VERSION,
            payload_length,
            digest,
        )
        + payload
    )


# ==============================================================
# DECODE
# ==============================================================


def decode_save(
    raw: bytes,
    *,
    signing_key: bytes | str,
    max_payload_size: int,
):
    """
    Verify and decode a Nexora save container.

    Authentication occurs BEFORE pickle parsing.
    """

    key = normalize_signing_key(
        signing_key
    )

    header_size = (
        _HEADER_STRUCT.size
    )

    if len(raw) < header_size:
        raise InvalidSaveError(
            "Save file is too small."
        )

    try:
        (
            magic,
            container_version,
            payload_length,
            stored_digest,
        ) = _HEADER_STRUCT.unpack(
            raw[
                :header_size
            ]
        )

    except struct.error as exc:
        raise InvalidSaveError(
            "Invalid Nexora save header."
        ) from exc

    # ----------------------------------------------------------
    # Magic
    # ----------------------------------------------------------

    if magic != MAGIC:
        raise InvalidSaveError(
            "File is not a Nexora save."
        )

    # ----------------------------------------------------------
    # Container version
    # ----------------------------------------------------------

    if (
        container_version
        != CONTAINER_VERSION
    ):
        raise UnsupportedSaveVersionError(
            "Unsupported Nexora save "
            f"container version: "
            f"{container_version}"
        )

    # ----------------------------------------------------------
    # Payload size
    # ----------------------------------------------------------

    if payload_length > max_payload_size:
        raise InvalidSaveError(
            "Save payload exceeds configured "
            "maximum size."
        )

    expected_file_size = (
        header_size
        + payload_length
    )

    if len(raw) != expected_file_size:
        raise InvalidSaveError(
            "Save payload length does not match header."
        )

    payload = raw[
        header_size:
    ]

    # ----------------------------------------------------------
    # VERIFY HMAC BEFORE UNPICKLING
    # ----------------------------------------------------------

    prefix = (
        _HEADER_PREFIX_STRUCT.pack(
            magic,
            container_version,
            payload_length,
        )
    )

    expected_digest = hmac.new(
        key,
        prefix + payload,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(
        stored_digest,
        expected_digest,
    ):
        raise SaveIntegrityError(
            "Save file authentication failed."
        )

    # ----------------------------------------------------------
    # Only now inspect pickle
    # ----------------------------------------------------------

    return restricted_loads(
        payload
    )