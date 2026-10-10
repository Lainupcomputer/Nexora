from __future__ import annotations

from typing import Any

from nexora.nodes.world.tilemap_node import TileMapNode
from nexora.tilemap import TileMap, TileSet


def register_world_nodes(registry) -> None:
    # ==========================================================
    # TileMapNode
    # ==========================================================

    def dump_tilemap_node(
        node: TileMapNode,
    ) -> dict[str, Any]:
        if (
            node.tilemap is None
            or node.tileset is None
        ):
            raise ValueError(
                f"TileMapNode {node.name!r} "
                "cannot be serialized without "
                "TileMap and TileSet"
            )

        state = {
            "centered": bool(
                node.centered
            ),
            "culling_enabled": bool(
                node.culling_enabled
            ),
            "culling_margin": int(
                node.culling_margin
            ),
            "base_render_layer": int(
                node.base_render_layer
            ),
        }
        if node.tilemap_asset:
            state["tilemap_asset"] = str(node.tilemap_asset)
        else:
            state["tilemap"] = node.tilemap.to_state()
            state["tileset"] = node.tileset.to_state()
        return state

    def load_tilemap_node(
        node: TileMapNode,
        state: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        assets = context.get(
            "assets"
        )

        if assets is None:
            raise RuntimeError(
                "Loading a serialized "
                "TileMapNode requires "
                "context['assets']"
            )

        asset_path = state.get("tilemap_asset")
        if asset_path:
            node.load_tilemap_asset(str(asset_path), assets)
        else:
            tilemap = TileMap.from_state(dict(state["tilemap"]))
            tileset = TileSet.from_state(dict(state["tileset"]))
            node.set_map_from_assets(tilemap, tileset, assets)

        node.centered = bool(
            state.get(
                "centered",
                True,
            )
        )

        node.culling_enabled = bool(
            state.get(
                "culling_enabled",
                True,
            )
        )

        node.culling_margin = int(
            state.get(
                "culling_margin",
                1,
            )
        )

        node.base_render_layer = int(
            state.get(
                "base_render_layer",
                0,
            )
        )

    registry.register(
        "TileMapNode",
        TileMapNode,
        dump_state=dump_tilemap_node,
        load_state=load_tilemap_node,
    )

