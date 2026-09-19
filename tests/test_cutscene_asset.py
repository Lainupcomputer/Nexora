from __future__ import annotations

from pathlib import Path

from nexora.cutscene import (
    CutsceneAsset,
    CutsceneKeyframe,
    CutscenePlayer,
    CutsceneTrack,
)


KEY = b"nexora-default-save-signing-key-change-this-for-your-game"


def test_cutscene_asset_round_trip_uses_secure_container(tmp_path: Path) -> None:
    asset = CutsceneAsset(name="Intro", duration=4.0)
    track = CutsceneTrack("Images", "image")
    track.add_keyframe(CutsceneKeyframe(0.0, {"path": "cutscenes/one.png"}))
    track.add_keyframe(CutsceneKeyframe(2.0, {"path": "cutscenes/two.png"}))
    asset.add_track(track)

    path = asset.save(tmp_path / "intro", signing_key=KEY)

    assert path.suffix == ".ncutscene"
    loaded = CutsceneAsset.load(path, signing_key=KEY)
    assert loaded.name == "Intro"
    assert loaded.tracks[0].keyframes[1].value["path"] == "cutscenes/two.png"


def test_cutscene_player_evaluates_step_tracks_and_events() -> None:
    events: list[tuple[str, dict]] = []
    asset = CutsceneAsset(name="Test", duration=3.0)
    image = CutsceneTrack("Image", "image")
    image.add_keyframe(CutsceneKeyframe(0.0, {"path": "a.png"}))
    image.add_keyframe(CutsceneKeyframe(2.0, {"path": "b.png"}))
    event = CutsceneTrack("Events", "event")
    event.add_keyframe(CutsceneKeyframe(1.0, {"id": "heartbeat", "parameters": {"volume": 0.5}}))
    asset.tracks = [image, event]

    player = CutscenePlayer(asset, on_event=lambda name, params: events.append((name, params)))
    player.play()
    player.update(1.5)

    assert player.snapshot()["Image"]["path"] == "a.png"
    assert events == [("heartbeat", {"volume": 0.5})]

    player.update(1.0)
    assert player.snapshot()["Image"]["path"] == "b.png"


def test_cutscene_player_interpolates_structured_values() -> None:
    asset = CutsceneAsset(name="Camera", duration=2.0)
    camera = CutsceneTrack("Camera", "camera")
    camera.add_keyframe(
        CutsceneKeyframe(
            0.0,
            {"x": 0.0, "y": 10.0, "zoom": 1.0},
            interpolation="linear",
        )
    )
    camera.add_keyframe(
        CutsceneKeyframe(
            2.0,
            {"x": 100.0, "y": 30.0, "zoom": 2.0},
        )
    )
    asset.tracks = [camera]

    player = CutscenePlayer(asset)
    player.play()
    player.update(1.0)

    assert player.snapshot()["Camera"] == {
        "x": 50.0,
        "y": 20.0,
        "zoom": 1.5,
    }
