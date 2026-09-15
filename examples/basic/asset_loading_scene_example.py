from __future__ import annotations

"""
Minimal integration snippet for Nexora's ordered asset loading pipeline.

The important part is build_load_task(). Plug the resulting SceneLoadTask into
an existing LoadingScene. Every LoadingScene update loads one asset and the
status automatically becomes e.g.:

    Initialisiere Assets: Font 100%
    Initialisiere Assets: Audio 0%
    Initialisiere Assets: Audio 50%
    Initialisiere Assets: Texture 0%
"""

from nexora.assets import AssetLoadCallbacks
from nexora.scene.loading import SceneLoadTask


def build_load_task(game) -> SceneLoadTask:
    task = SceneLoadTask("Asset Workflow Demo")

    callbacks = AssetLoadCallbacks(
        on_stage_started=lambda p: print(p.status),
        on_progress=lambda p: print(p.status),
        on_asset_loaded=lambda p: print("Loaded:", p.asset_path),
        on_completed=lambda: print("Assets ready"),
        on_failed=lambda exc: print("Asset loading failed:", exc),
    )

    game.assets.add_loading_stages(
        task,
        fonts=[
            ("fonts/Roboto-Regular.ttf", 24.0),
            ("fonts/Roboto-Bold.ttf", 32.0),
        ],
        sounds=[
            "audio/kick.wav",
            "audio/snare.wav",
            "audio/hihat.wav",
        ],
        textures=[
            "characters/punk_idle_8x64x128.png",
            "characters/punk_walk_8x64x128.png",
        ],
        callbacks=callbacks,
    )

    return task
