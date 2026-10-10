from __future__ import annotations

from ..property import InspectorProperty
from nexora.nodes.camera.camera_2d import Camera2D

def register_camera_defaults(registry) -> None:
    registry.register(
            Camera2D,
            InspectorProperty(
                "camera_active",
                "Active",
                "active",
                kind="bool",
                group="Camera",
            ),
            InspectorProperty(
                "camera_zoom",
                "Zoom",
                "zoom",
                kind="float",
                group="Camera",
                decimals=3,
            ),
            InspectorProperty(
                "camera_clamp",
                "Clamp Bounds",
                "clamp_to_bounds",
                kind="bool",
                group="Camera",
            ),
            InspectorProperty(
                "camera_trauma",
                "Trauma",
                "trauma",
                kind="float",
                group="Camera Effects",
                decimals=3,
            ),
            InspectorProperty(
                "camera_trauma_decay",
                "Trauma Decay",
                "trauma_decay",
                kind="float",
                group="Camera Effects",
                decimals=3,
            ),
            InspectorProperty(
                "camera_trauma_strength",
                "Trauma Strength",
                "trauma_strength",
                kind="float",
                group="Camera Effects",
                decimals=3,
            ),
            InspectorProperty(
                "camera_trauma_power",
                "Trauma Power",
                "trauma_power",
                kind="float",
                group="Camera Effects",
                decimals=3,
            ),
            InspectorProperty(
                "camera_fade_alpha",
                "Fade Alpha",
                "fade_alpha",
                kind="float",
                group="Camera Effects",
                decimals=3,
            ),
            InspectorProperty(
                "camera_flash_alpha",
                "Flash Alpha",
                "flash_alpha",
                kind="float",
                group="Camera Effects",
                decimals=3,
            ),
            InspectorProperty(
                "camera_letterbox",
                "Letterbox",
                "letterbox_size",
                kind="float",
                group="Camera Effects",
                decimals=3,
            ),
        )
