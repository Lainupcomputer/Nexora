from __future__ import annotations

from nexora.cutscene import (
    DEFAULT_CUTSCENE_SIGNING_KEY,
    CutsceneAsset,
    CutsceneKeyframe,
    CutscenePlayerNode,
    CutsceneTrack,
)
from nexora.ecs.world import World
from nexora.scene.serialization.common import node_to_state
from nexora.scene.serialization.registry import NodeFactoryRegistry


class _RenderCamera:
    x = 0.0
    y = 0.0
    zoom = 1.0

    def set_position(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def set_zoom(self, zoom):
        self.zoom = float(zoom)


class _Renderer:
    def __init__(self):
        self.camera = _RenderCamera()


class _Assets:
    def __init__(self, root):
        self.root = root
        self.requests = []

    def texture(self, path):
        self.requests.append(str(path))
        return object()


def test_cutscene_player_node_applies_tracks_and_keeps_runtime_children_out_of_scene_state(tmp_path):
    project = tmp_path / "project"
    cutscene_path = project / "cutscenes" / "intro.ncutscene"
    asset = CutsceneAsset(
        name="Intro",
        duration=2.0,
        tracks=[
            CutsceneTrack(
                "Image",
                "image",
                keyframes=[
                    CutsceneKeyframe(0.0, {"path": "scene.png", "width": 320})
                ],
            ),
            CutsceneTrack(
                "Camera",
                "camera",
                keyframes=[CutsceneKeyframe(0.0, {"x": 8, "y": 12, "zoom": 2})],
            ),
            CutsceneTrack(
                "Fade",
                "fade",
                keyframes=[CutsceneKeyframe(0.0, {"alpha": 0.25})],
            ),
            CutsceneTrack(
                "Events",
                "event",
                keyframes=[CutsceneKeyframe(0.5, {"id": "ready", "parameters": {"ok": True}})],
            ),
        ],
    )
    asset.save(cutscene_path, signing_key=DEFAULT_CUTSCENE_SIGNING_KEY)

    node = CutscenePlayerNode("IntroPlayer", World())
    assets = _Assets(project / "assets")
    renderer = _Renderer()
    events = []
    node.event.connect(lambda event_id, parameters: events.append((event_id, parameters)))
    node.build(
        renderer=renderer,
        assets=assets,
        asset_path="cutscenes/intro.ncutscene",
        signing_key=DEFAULT_CUTSCENE_SIGNING_KEY,
    )
    node.play(restart=True)
    node.update(0.5)

    assert node.sprite is not None
    assert node.sprite.texture is not None
    assert node.sprite.width == 320
    assert node.camera is not None
    assert node.camera.position == (8.0, 12.0)
    assert renderer.camera.zoom == 2.0
    assert node.camera.fade_alpha == 0.25
    assert events == [("ready", {"ok": True})]

    state = node_to_state(node, NodeFactoryRegistry())
    assert state["type"] == "CutscenePlayerNode"
    assert state["children"] == []

