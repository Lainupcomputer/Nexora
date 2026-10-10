from __future__ import annotations

from ..property import InspectorProperty
from nexora.nodes.texture.animated_sprite import AnimatedSprite
from nexora.nodes.world.tilemap_node import TileMapNode

def register_base_defaults(registry, node_type: type) -> None:
    registry.register(
            node_type,
            InspectorProperty(
                "name",
                "Name",
                "name",
                kind="text",
                group="Node",
            ),
            InspectorProperty(
                "enabled",
                "Enabled",
                "enabled",
                kind="bool",
                group="Node",
            ),
            InspectorProperty(
                "visible",
                "Visible",
                "visible",
                kind="bool",
                group="Node",
            ),
            InspectorProperty(
                "position_x",
                "Position X",
                "transform.x",
                kind="float",
                group="Transform",
                decimals=3,
            ),
            InspectorProperty(
                "position_y",
                "Position Y",
                "transform.y",
                kind="float",
                group="Transform",
                decimals=3,
            ),
            InspectorProperty(
                "rotation",
                "Rotation",
                "transform.rotation",
                kind="float",
                group="Transform",
                decimals=3,
            ),
            InspectorProperty(
                "scale_x",
                "Scale X",
                "transform.scale_x",
                kind="float",
                group="Transform",
                decimals=3,
            ),
            InspectorProperty(
                "scale_y",
                "Scale Y",
                "transform.scale_y",
                kind="float",
                group="Transform",
                decimals=3,
            ),
        )

    registry.register(
            AnimatedSprite,
            InspectorProperty("sprite_width", "Width", "width", kind="float", group="Sprite", decimals=2),
            InspectorProperty("sprite_height", "Height", "height", kind="float", group="Sprite", decimals=2),
            InspectorProperty("sprite_alpha", "Alpha", "alpha", kind="float", group="Sprite", decimals=3),
            InspectorProperty("sprite_flip_x", "Flip X", "flip_x", kind="bool", group="Sprite"),
            InspectorProperty("sprite_flip_y", "Flip Y", "flip_y", kind="bool", group="Sprite"),
        )

    registry.register(
            TileMapNode,
            InspectorProperty(
                "tilemap_asset",
                "TileMap Asset",
                "tilemap_asset",
                kind="text",
                group="TileMap",
                editable=False,
            ),
        )
