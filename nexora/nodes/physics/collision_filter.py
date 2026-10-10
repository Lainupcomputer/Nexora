from __future__ import annotations


def collision_layer_bit(layer: int) -> int:
    layer = int(layer)
    if layer <= 0:
        raise ValueError(
            "Collision layer number must be greater than zero."
        )
    return 1 << (layer - 1)


def add_collision_mask(mask: int, layer: int) -> int:
    return int(mask) | collision_layer_bit(layer)


def remove_collision_mask(mask: int, layer: int) -> int:
    return int(mask) & ~collision_layer_bit(layer)


def has_collision_mask(mask: int, layer: int) -> bool:
    return bool(int(mask) & collision_layer_bit(layer))
