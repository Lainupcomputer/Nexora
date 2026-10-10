from __future__ import annotations

from typing import Any


def register_cutscene_nodes(registry) -> None:
    # Imported lazily because cutscene assets depend on scene serialization.
    from nexora.gameplay.cutscene.node import CutscenePlayerNode
    # ==========================================================
    # Cutscene player
    # ==========================================================

    def dump_cutscene_player(
        node: CutscenePlayerNode,
    ) -> dict[str, Any]:
        return {
            "asset_path": node.asset_path,
            "autoplay": bool(node.autoplay),
            "play_on_enter": bool(node.play_on_enter),
            "loop": bool(node.loop),
        }

    def load_cutscene_player(
        node: CutscenePlayerNode,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        asset_path = state.get("asset_path")
        node.asset_path = None if asset_path is None else str(asset_path)
        node.autoplay = bool(state.get("autoplay", False))
        node.play_on_enter = bool(state.get("play_on_enter", node.autoplay))
        node.loop = bool(state.get("loop", False))

        renderer = context.get("renderer")
        assets = context.get("assets")
        if node.asset_path and renderer is not None and assets is not None:
            node.build(
                renderer=renderer,
                assets=assets,
                audio=context.get("audio"),
                scene=context.get("scene"),
                scene_path=context.get("scene_path"),
                signing_key=(
                    context.get("scene_signing_key")
                    or context.get("save_signing_key")
                ),
            )

    registry.register(
        "CutscenePlayerNode",
        CutscenePlayerNode,
        dump_state=dump_cutscene_player,
        load_state=load_cutscene_player,
    )
