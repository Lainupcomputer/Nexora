from __future__ import annotations

from collections import defaultdict

from .property import InspectorProperty


class InspectorRegistry:
    """Property metadata registry used by the Nexora editor inspector."""

    def __init__(self) -> None:
        self._by_type: dict[type, list[InspectorProperty]] = defaultdict(list)

    def register(
        self,
        node_type: type,
        *properties: InspectorProperty,
    ) -> None:
        items = self._by_type[node_type]
        known = {item.key for item in items}

        for item in properties:
            if item.key in known:
                continue

            items.append(item)
            known.add(item.key)

    def properties_for(self, node) -> tuple[InspectorProperty, ...]:
        result: list[InspectorProperty] = []
        seen: set[str] = set()

        # Generic properties first, subclass-specific properties after.
        for node_type in reversed(type(node).__mro__):
            for prop in self._by_type.get(node_type, ()):
                if prop.key in seen:
                    continue

                result.append(prop)
                seen.add(prop.key)

        return tuple(result)

    def registered_properties(
        self,
    ) -> tuple[InspectorProperty, ...]:
        """Return all registered properties in stable registration order."""

        result: list[InspectorProperty] = []
        seen: set[str] = set()

        for properties in self._by_type.values():
            for prop in properties:
                if prop.key in seen:
                    continue

                result.append(prop)
                seen.add(prop.key)

        return tuple(result)

def create_default_inspector_registry(node_type: type) -> InspectorRegistry:
    """Create Nexora's built-in Inspector property registry."""

    from .defaults import (
        register_animation_defaults,
        register_base_defaults,
        register_camera_defaults,
        register_effect_defaults,
        register_navigation_defaults,
        register_physics_defaults,
    )

    registry = InspectorRegistry()
    register_base_defaults(registry, node_type)
    register_physics_defaults(registry)
    register_navigation_defaults(registry)
    register_camera_defaults(registry)
    register_effect_defaults(registry)
    register_animation_defaults(registry)
    return registry
