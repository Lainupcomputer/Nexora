from nexora.editor.app import EditorApp, resolve_project_path, run_editor
from nexora.editor.model import EditorDocument, ProjectModel, SelectionService
from nexora.editor.tilemap import TileMapEditorModel
from nexora.editor.tilemap_app import TileMapEditorApp, TileMapEditorScene, run_tilemap_editor
from nexora.editor.standalone_tilemap_editor import (
    StandaloneTileMapEditorApp,
    StandaloneTileMapEditorScene,
    run_standalone_tilemap_editor,
)
from nexora.editor.item_editor import (
    ItemEditorApp,
    ItemEditorScene,
    run_item_editor,
)
from nexora.editor.tools import (
    EditorToolsApp,
    EditorToolsScene,
    run_editor_tools,
)
from nexora.editor.cutscene_editor import (
    CutsceneEditorApp,
    CutsceneEditorScene,
    run_cutscene_editor,
)

# ``--tilemapedit`` now opens the independent low-level editor.  Keep the
# legacy names above available for existing integrations and tests.
run_tilemap_editor = run_standalone_tilemap_editor

__all__ = [
    "EditorApp",
    "EditorDocument",
    "ProjectModel",
    "SelectionService",
    "TileMapEditorModel",
    "TileMapEditorApp",
    "TileMapEditorScene",
    "resolve_project_path",
    "run_editor",
    "run_tilemap_editor",
    "StandaloneTileMapEditorApp",
    "StandaloneTileMapEditorScene",
    "run_standalone_tilemap_editor",
    "ItemEditorApp",
    "ItemEditorScene",
    "run_item_editor",
    "EditorToolsApp",
    "EditorToolsScene",
    "run_editor_tools",
    "CutsceneEditorApp",
    "CutsceneEditorScene",
    "run_cutscene_editor",
]
