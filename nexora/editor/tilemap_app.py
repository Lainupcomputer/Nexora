"""Backward-compatible facade for the standalone TileMap editor.

The active ``--tilemapedit`` command uses
``nexora.editor.standalone_tilemap_editor``.  The former node-based editor is
no longer loaded; these aliases keep the old module import path working.
"""

from .standalone_tilemap_editor import (
    StandaloneTileMapEditorApp as TileMapEditorApp,
    StandaloneTileMapEditorScene as TileMapEditorScene,
    run_standalone_tilemap_editor as run_tilemap_editor,
)

__all__ = ["TileMapEditorApp", "TileMapEditorScene", "run_tilemap_editor"]
