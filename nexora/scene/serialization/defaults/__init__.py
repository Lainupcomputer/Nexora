from __future__ import annotations


def register_default_nodes(registry) -> None:
    # Imports stay local so registry.py itself remains lightweight and avoids
    # cycles with node and cutscene modules during package initialization.
    from .core import register_core_nodes
    from .physics import register_physics_nodes
    from .navigation import register_navigation_nodes
    from .effects import register_effect_nodes
    from .world import register_world_nodes
    from .cutscene import register_cutscene_nodes

    register_core_nodes(registry)
    register_physics_nodes(registry)
    register_navigation_nodes(registry)
    register_effect_nodes(registry)
    register_world_nodes(registry)
    register_cutscene_nodes(registry)


__all__ = ["register_default_nodes"]
