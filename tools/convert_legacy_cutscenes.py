from __future__ import annotations

"""Convert the original BirthScene/DeathScene timelines to .ncutscene.

This tool intentionally uses only the standard library so it can be run from
the project bootstrap even before SDL/GPU services are initialized.
"""

import hashlib
import hmac
import pickle
import struct
from pathlib import Path
from typing import Any


KEY = b"nexora-default-save-signing-key-change-this-for-your-game"
MAGIC = b"NXCUT001"
HEADER = struct.Struct(">8sHQ32s")
PREFIX = struct.Struct(">8sHQ")


def keyframe(time: float, value: Any, interpolation: str = "step") -> dict[str, Any]:
    return {"time": float(time), "value": value, "interpolation": interpolation}


def track(name: str, track_type: str, frames: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "type": track_type,
        "target": "",
        "enabled": True,
        "keyframes": frames,
    }


def image_frames(paths: tuple[str, ...], times: tuple[float, ...]) -> list[dict[str, Any]]:
    return [keyframe(time, {"path": path}) for path, time in zip(paths, times)]


def camera_keyframes() -> list[dict[str, Any]]:
    # Endpoints of the original CinematicCamera2D moves.  A keyframe's
    # interpolation controls the segment that follows it.
    points = [
        (0.00, 0.0, 0.0, 1.00, "step"),
        (1.15, 0.0, 0.0, 1.00, "ease_in_out"),
        (3.65, -22.0, 0.0, 1.40, "ease_in_out"),
        (7.15, -222.0, 50.0, 3.40, "step"),
        (14.79, -222.0, 50.0, 3.40, "ease_in_out"),
        (17.59, 20.0, -8.0, 1.05, "step"),
        (21.23, 20.0, -8.0, 1.05, "ease_out"),
        (23.63, 34.0, 2.0, 1.09, "step"),
        (25.77, 34.0, 2.0, 1.09, "ease_out"),
        (26.97, -20.0, 8.0, 1.13, "step"),
        (28.11, -20.0, 8.0, 1.13, "ease_in_out"),
        (29.11, 0.0, 0.0, 1.10, "step"),
        (35.45, 0.0, 0.0, 1.10, "ease_out"),
        (38.45, 18.0, -5.0, 0.96, "step"),
        (42.09, 18.0, -5.0, 0.96, "ease_in_out"),
        (45.09, -4.0, 4.0, 1.08, "step"),
        (48.29, -4.0, 4.0, 1.08, "step"),
        (55.27, 0.0, 0.0, 1.16, "step"),
        (58.77, 0.0, 0.0, 1.16, "step"),
        (75.80, 0.0, 0.0, 1.16, "ease_out"),
        (80.30, 0.0, 10.0, 1.02, "step"),
        (84.30, 0.0, 10.0, 1.02, "step"),
    ]
    return [
        keyframe(time, {"x": x, "y": y, "zoom": zoom}, interpolation)
        for time, x, y, zoom, interpolation in points
    ]


def fade_keyframes() -> list[dict[str, Any]]:
    black = [0.0, 0.0, 0.0]
    white = [1.0, 1.0, 1.0]
    red_black = [0.08, 0.015, 0.015]
    blue_black = [0.01, 0.015, 0.04]
    purple_black = [0.025, 0.01, 0.035]
    points = [
        (0.00, 1.0, white, "step"),
        (0.45, 1.0, white, "linear"),
        (1.15, 0.0, white, "step"),
        (14.15, 0.0, white, "step"),
        (14.43, 1.0, black, "linear"),
        (14.51, 1.0, black, "step"),
        (14.79, 0.0, black, "linear"),
        (20.59, 0.0, black, "step"),
        (20.87, 1.0, black, "linear"),
        (20.95, 1.0, black, "step"),
        (21.23, 0.0, black, "linear"),
        (25.13, 0.0, black, "step"),
        (25.41, 1.0, black, "linear"),
        (25.49, 1.0, black, "step"),
        (25.77, 0.0, black, "linear"),
        (27.47, 0.0, black, "step"),
        (27.75, 1.0, white, "linear"),
        (27.83, 1.0, white, "step"),
        (28.11, 0.0, white, "linear"),
        (33.33, 0.0, white, "step"),
        (33.53, 1.0, red_black, "linear"),
        (33.61, 1.0, red_black, "step"),
        (33.81, 0.0, red_black, "linear"),
        (34.81, 0.0, red_black, "step"),
        (35.09, 1.0, black, "linear"),
        (35.17, 1.0, black, "step"),
        (35.45, 0.0, black, "linear"),
        (41.45, 0.0, black, "step"),
        (41.73, 1.0, black, "linear"),
        (41.81, 1.0, black, "step"),
        (42.09, 0.0, black, "linear"),
        (54.29, 0.0, black, "step"),
        (54.74, 1.0, blue_black, "linear"),
        (54.82, 1.0, blue_black, "step"),
        (55.27, 0.0, blue_black, "linear"),
        (74.22, 0.0, blue_black, "step"),
        (74.97, 1.0, purple_black, "linear"),
        (75.05, 1.0, purple_black, "step"),
        (75.80, 0.0, purple_black, "linear"),
        (85.00, 0.0, black, "step"),
        (86.25, 1.0, black, "linear"),
        (86.50, 1.0, white, "step"),
        (87.60, 1.0, white, "step"),
    ]
    return [
        keyframe(time, {"alpha": alpha, "color": color}, interpolation)
        for time, alpha, color, interpolation in points
    ]


def audio(path: str, *, channel: str = "sfx", volume: float = 1.0, **options: Any) -> dict[str, Any]:
    return {"path": path, "channel": channel, "volume": volume, "optional": True, **options}


def birth_asset() -> dict[str, Any]:
    paths = tuple(f"cutscenes/birth/birth_{index}.png" for index in range(1, 7))
    start_times = (0.0, 19.3, 51.7, 76.3, 108.9, 138.5)
    audio_frames = [
        keyframe(0.0, audio("audio/birth_scene/theme.wav", channel="music", volume=0.34, stream=True, loop=True, fade_in=2.5)),
        keyframe(0.0, audio("audio/birth_scene/room_ambience.wav", channel="ambient", volume=0.10, stream=True, loop=True, fade_in=2.5)),
        keyframe(2.5, audio("audio/birth_scene/clock_tick.wav", volume=0.18)),
        keyframe(18.5, audio("audio/birth_scene/transition_whoosh.wav", volume=0.20)),
        keyframe(20.1, audio("audio/birth_scene/cloth_movement.wav", volume=0.28)),
        keyframe(50.1, audio("audio/birth_scene/transition_whoosh.wav", volume=0.20)),
        keyframe(51.7, audio("audio/birth_scene/door_metal.wav", volume=0.42)),
        keyframe(51.7, audio("audio/birth_scene/metal_latch.wav", volume=0.24)),
        keyframe(74.7, audio("audio/birth_scene/transition_whoosh.wav", volume=0.20)),
        keyframe(76.3, audio("audio/birth_scene/cloth_movement.wav", volume=0.28)),
        keyframe(107.3, audio("audio/birth_scene/transition_whoosh.wav", volume=0.20)),
        keyframe(108.9, audio("audio/birth_scene/soft_birth_chime.wav", volume=0.32)),
        keyframe(136.9, audio("audio/birth_scene/transition_whoosh.wav", volume=0.20)),
        keyframe(175.5, audio("audio/birth_scene/transition_whoosh.wav", volume=0.20)),
        keyframe(175.5, audio("audio/birth_scene/theme.wav", action="fade_out", duration=2.5)),
        keyframe(175.5, audio("audio/birth_scene/room_ambience.wav", action="fade_out", duration=2.5)),
    ]
    return {
        "format": "nexora_cutscene",
        "version": 1,
        "name": "Birth Prologue",
        "duration": 178.0,
        "fps": 60.0,
        "tracks": [
            track("Birth Images", "image", image_frames(paths, start_times)),
            track("Camera", "camera", [keyframe(0.0, {"x": 0.0, "y": 0.0, "zoom": 1.0})]),
            track("Fade", "fade", _birth_fade_frames()),
            track("Audio", "audio", audio_frames),
            track("Events", "event", [keyframe(178.0, {"id": "birth_finished", "parameters": {}})]),
        ],
        "metadata": {
            "legacy_scene": "BirthScene",
            "light": {
                "anchor": [96.0, 178.0],
                "radius": 68.0,
                "color": [1.0, 0.48, 0.12],
                "intensity": 0.95,
                "falloff": 1.7,
                "flicker": True,
                "flicker_strength": 0.16,
                "flicker_speed": 11.5,
            },
        },
    }


def _birth_fade_frames() -> list[dict[str, Any]]:
    white = [1.0, 1.0, 1.0]
    points = [
        (0.0, 1.0, "step"), (2.5, 0.0, "linear"),
        (18.5, 0.0, "step"), (19.3, 1.0, "linear"), (20.1, 0.0, "linear"),
        (50.1, 0.0, "step"), (50.9, 1.0, "linear"), (51.7, 0.0, "linear"),
        (74.7, 0.0, "step"), (75.5, 1.0, "linear"), (76.3, 0.0, "linear"),
        (107.3, 0.0, "step"), (108.1, 1.0, "linear"), (108.9, 0.0, "linear"),
        (136.9, 0.0, "step"), (137.7, 1.0, "linear"), (138.5, 0.0, "linear"),
        (175.5, 0.0, "step"), (178.0, 1.0, "linear"),
    ]
    return [keyframe(time, {"alpha": alpha, "color": white}, interpolation) for time, alpha, interpolation in points]


def death_asset() -> dict[str, Any]:
    paths = tuple(
        f"cutscenes/death/{index:02d}_{name}.png"
        for index, name in enumerate(
            (
                "city_establishing", "crossing_wait", "truck_approaching", "realization",
                "rescue_push", "impact_flash", "aftermath", "holding_hand", "fading_pov",
                "reincarnation_transition",
            ),
            1,
        )
    )
    image_times = (0.0, 14.43, 20.87, 25.41, 27.75, 33.53, 35.09, 41.73, 54.74, 74.97)
    voices = [1.15, 14.79, 21.23, 25.77, 28.11, 35.45, 42.09, 55.27]
    audio_frames = [
        *[
            keyframe(time, audio(f"audio/death_scene/death_{frame}.wav", channel="voice", stream=True))
            for frame, time in zip((1, 2, 3, 4, 5, 7, 8, 9), voices)
        ],
        keyframe(32.61, audio("audio/death_scene/crash.wav", volume=1.0)),
        keyframe(32.61, audio("audio/death_scene/metal_impact.wav", volume=0.34)),
        keyframe(35.45, audio("audio/death_scene/theme.wav", channel="music", volume=0.12, stream=True, loop=True, fade_in=2.0)),
        keyframe(42.09, audio("audio/death_scene/jonas_breath.wav", volume=0.24)),
        keyframe(86.50, audio("audio/death_scene/theme.wav", action="fade_out", duration=1.5)),
        keyframe(86.50, audio("audio/death_scene/wind_fade.wav", volume=0.22)),
    ]
    heartbeat_time = 42.09
    heartbeat_elapsed = 0.0
    while heartbeat_time < 87.60:
        audio_frames.append(keyframe(heartbeat_time, audio("audio/death_scene/heartbeat.wav", volume=0.78)))
        interval_progress = min(1.0, heartbeat_elapsed / 18.0)
        interval = max(0.18, 1.0 - 0.82 * interval_progress)
        heartbeat_time += interval
        heartbeat_elapsed += interval

    effects = [
        keyframe(0.0, {"effect": "letterbox", "size": 82.0, "duration": 0.45}),
        keyframe(32.61, {"effect": "flash", "amount": 0.88, "duration": 0.14, "color": [1.0, 0.93, 0.78]}),
        keyframe(32.61, {"effect": "punch", "x": 34.0, "y": -18.0, "duration": 0.22}),
        keyframe(32.61, {"effect": "trauma", "amount": 0.68}),
        keyframe(58.41, {"effect": "trauma", "amount": 0.16}),
        keyframe(84.30, {"effect": "letterbox", "size": 0.0, "duration": 0.70}),
        keyframe(86.50, {"effect": "flash", "amount": 1.0, "duration": 0.35, "color": [1.0, 1.0, 1.0]}),
    ]
    return {
        "format": "nexora_cutscene",
        "version": 1,
        "name": "Death Prologue",
        "duration": 87.60,
        "fps": 60.0,
        "tracks": [
            track("Death Images", "image", image_frames(paths, image_times)),
            track("Camera", "camera", camera_keyframes()),
            track("Fade", "fade", _death_fade_frames()),
            track("Effects", "effect", effects),
            track("Audio", "audio", audio_frames),
            track("Events", "event", [keyframe(87.60, {"id": "open_birth_scene", "parameters": {}})]),
        ],
        "metadata": {"legacy_scene": "DeathScene", "next_cutscene": "cutscenes/birth_prologue.ncutscene"},
    }


def _death_fade_frames() -> list[dict[str, Any]]:
    colors = {
        "black": [0.0, 0.0, 0.0],
        "red": [0.08, 0.015, 0.015],
        "blue": [0.01, 0.015, 0.04],
        "purple": [0.025, 0.01, 0.035],
        "white": [1.0, 1.0, 1.0],
    }
    points = [
        (0.0, 1.0, "black", "step"), (1.15, 0.0, "black", "linear"),
        (14.15, 0.0, "black", "step"), (14.43, 1.0, "black", "linear"), (14.79, 0.0, "black", "linear"),
        (20.59, 0.0, "black", "step"), (20.87, 1.0, "black", "linear"), (21.23, 0.0, "black", "linear"),
        (25.13, 0.0, "black", "step"), (25.41, 1.0, "black", "linear"), (25.77, 0.0, "black", "linear"),
        (27.47, 0.0, "black", "step"), (27.75, 1.0, "white", "linear"), (28.11, 0.0, "white", "linear"),
        (32.97, 0.0, "white", "step"), (33.17, 1.0, "red", "linear"), (33.45, 0.0, "red", "linear"),
        (34.45, 0.0, "red", "step"), (34.73, 1.0, "black", "linear"), (35.09, 0.0, "black", "linear"),
        (41.09, 0.0, "black", "step"), (41.37, 1.0, "black", "linear"), (41.73, 0.0, "black", "linear"),
        (53.93, 0.0, "black", "step"), (54.38, 1.0, "blue", "linear"), (54.91, 0.0, "blue", "linear"),
        (73.86, 0.0, "blue", "step"), (74.61, 1.0, "purple", "linear"), (75.44, 0.0, "purple", "linear"),
        (84.64, 0.0, "black", "step"), (85.89, 1.0, "black", "linear"),
        (86.14, 1.0, "white", "step"), (86.89, 1.0, "white", "step"),
    ]
    return [keyframe(time, {"alpha": alpha, "color": colors[color]}, interpolation) for time, alpha, color, interpolation in points]


def write_asset(path: Path, state: dict[str, Any]) -> None:
    payload = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
    prefix = PREFIX.pack(MAGIC, 1, len(payload))
    digest = hmac.new(KEY, prefix + payload, hashlib.sha256).digest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(HEADER.pack(MAGIC, 1, len(payload), digest) + payload)


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    write_asset(project / "cutscenes" / "birth_prologue.ncutscene", birth_asset())
    write_asset(project / "cutscenes" / "death_prologue.ncutscene", death_asset())
    print("Converted birth_prologue.ncutscene and death_prologue.ncutscene")


if __name__ == "__main__":
    main()
