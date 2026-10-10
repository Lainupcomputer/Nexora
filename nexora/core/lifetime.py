from __future__ import annotations


def owner_is_alive(owner: object | None, owner_ref) -> bool:
    """Return whether an optional runtime owner should still be considered alive."""
    if owner is None and owner_ref is not None:
        return False
    if owner is None:
        return True

    world = getattr(owner, "world", None)
    entity = getattr(owner, "entity", None)
    is_alive = getattr(world, "is_alive", None)

    if entity is not None and callable(is_alive):
        try:
            return bool(is_alive(entity))
        except Exception:
            return True

    return True
