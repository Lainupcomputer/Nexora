from nexora.nodes import (
    Node,
    UINode,
    UIRoot,
)

from nexora.scene.loading import (
    LoadingProgress,
    LoadingStage,
    LoadingState,
    SceneLoadTask,
)

from nexora.scene.loading_scene import (
    LoadingScene,
)

from nexora.scene.manager import (
    SceneManager,
)

from nexora.scene.scene import (
    Scene,
    SceneState,
)

from nexora.scene.transition import (
    FadeSceneTransition,
    SceneTransition,
)


__all__ = [
    # ----------------------------------------------------------
    # Core scenes
    # ----------------------------------------------------------
    "Scene",
    "SceneState",
    "SceneManager",

    # ----------------------------------------------------------
    # Transitions
    # ----------------------------------------------------------
    "SceneTransition",
    "FadeSceneTransition",

    # ----------------------------------------------------------
    # Loading
    # ----------------------------------------------------------
    "LoadingScene",
    "LoadingProgress",
    "LoadingStage",
    "LoadingState",
    "SceneLoadTask",

    # ----------------------------------------------------------
    # Nodes exposed through scene API
    # ----------------------------------------------------------
    "Node",
    "UINode",
    "UIRoot",
]