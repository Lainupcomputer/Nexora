from __future__ import annotations

from nexora.editor.inspector import (
    InspectorProperty,
    create_default_inspector_registry,
)
from nexora.nodes.node import Node
from nexora.nodes.effects import Light2D, LightOccluder2D
from nexora.nodes.entity.character_body_2d import CharacterBody2D
from nexora.nodes.entity.ray_cast_2d import RayCast2D
from nexora.nodes.navigation.navigation_agent_2d import NavigationAgent2D


def _keys(registry, node_type):
    node = object.__new__(node_type)
    return {
        prop.key
        for prop in registry.properties_for(node)
    }


def test_inspector_property_accepts_int_kind():
    prop = InspectorProperty(
        "layer",
        "Layer",
        "collision_layer",
        kind="int",
    )

    assert prop.kind == "int"


def test_registered_properties_contains_node_specific_metadata():
    registry = create_default_inspector_registry(Node)

    keys = {
        prop.key
        for prop in registry.registered_properties()
    }

    assert "name" in keys
    assert "collision_layer" in keys
    assert "light_radius" in keys
    assert "nav_repath_interval" in keys


def test_character_body_inherits_body_and_motion_properties():
    registry = create_default_inspector_registry(Node)
    keys = _keys(registry, CharacterBody2D)

    assert "collision_layer" in keys
    assert "collision_mask" in keys
    assert "velocity_x" in keys
    assert "velocity_y" in keys


def test_light_has_lighting_shadow_and_effect_properties():
    registry = create_default_inspector_registry(Node)
    keys = _keys(registry, Light2D)

    assert "light_radius" in keys
    assert "light_intensity" in keys
    assert "light_cast_shadows" in keys
    assert "light_shadow_softness" in keys
    assert "light_flicker_enabled" in keys
    assert "light_pulse_enabled" in keys


def test_light_occluder_has_occluder_properties():
    registry = create_default_inspector_registry(Node)
    keys = _keys(registry, LightOccluder2D)

    assert "occluder_closed" in keys
    assert "occluder_enabled" in keys
    assert "occluder_mask" in keys


def test_raycast_has_raycast_properties():
    registry = create_default_inspector_registry(Node)
    keys = _keys(registry, RayCast2D)

    assert "ray_target_x" in keys
    assert "ray_target_y" in keys
    assert "ray_collision_mask" in keys
    assert "ray_enabled" in keys


def test_navigation_agent_has_navigation_and_avoidance_properties():
    registry = create_default_inspector_registry(Node)
    keys = _keys(registry, NavigationAgent2D)

    assert "nav_layer" in keys
    assert "nav_auto_repath" in keys
    assert "nav_repath_interval" in keys
    assert "nav_avoidance_enabled" in keys
    assert "nav_avoidance_radius" in keys
