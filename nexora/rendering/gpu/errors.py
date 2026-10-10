from __future__ import annotations


def decode_sdl_error(error) -> str:
    if isinstance(error, bytes):
        return error.decode("utf-8", errors="replace")
    if error is None:
        return "<unknown SDL error>"
    return str(error)
