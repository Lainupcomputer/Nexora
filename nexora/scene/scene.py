from __future__ import annotations

from enum import Enum

from nexora.ecs.world import World
from nexora.nodes.node import Node
from nexora.nodes.ui.controls.text_input import TextInput
from nexora.nodes.ui.ui_root import UIRoot
from nexora.ui import UIInput
from nexora.physics import (
    get_physics_world,
)


class SceneState(str, Enum):
    """
    Current lifecycle state of a scene.
    """

    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"
    DESTROYED = "destroyed"


class Scene:
    """
    A hierarchical collection of nodes backed by an ECS world.

    A Scene owns:

        - ECS World
        - root Node
        - UI root
        - UI input state
        - primary camera
        - lifecycle state

    Lifecycle
    ---------

    CREATED
        Scene exists but has not been entered yet.

    ACTIVE
        Scene receives update, fixed update, input and rendering.

    PAUSED
        Scene remains loaded but does not receive update,
        fixed update or input.

        Rendering is still allowed so overlay scenes can render
        on top of the paused scene.

    INACTIVE
        Scene is loaded but currently not active.

    DESTROYED
        Scene resources have been released.
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        if not name:
            raise ValueError(
                "Scene name cannot be empty."
            )

        self.name = str(
            name
        )

        # ======================================================
        # ECS
        # ======================================================

        self.world = World()

        # ======================================================
        # Root node
        # ======================================================

        self.root = Node(
            "Root",
            self.world,
        )

        # ======================================================
        # UI
        # ======================================================

        self.ui = UIRoot(
            "UI",
            self.world,
        )

        self.ui_input = UIInput()

        # ======================================================
        # Primary camera
        # ======================================================

        self._camera: Node | None = None

        # ======================================================
        # Lifecycle
        # ======================================================

        self._state = (
            SceneState.CREATED
        )

        self._destroyed = False

    # ==========================================================
    # LIFECYCLE PROPERTIES
    # ==========================================================

    @property
    def state(
        self,
    ) -> SceneState:
        return self._state

    @property
    def active(
        self,
    ) -> bool:
        return (
            self._state
            == SceneState.ACTIVE
        )

    @property
    def paused(
        self,
    ) -> bool:
        return (
            self._state
            == SceneState.PAUSED
        )

    @property
    def destroyed(
        self,
    ) -> bool:
        return self._destroyed

    # ==========================================================
    # PRIMARY CAMERA
    # ==========================================================

    @property
    def camera(
        self,
    ) -> Node | None:
        """
        Return the primary camera assigned to this scene.

        The primary camera can be used by:

            - scene transitions
            - camera effects
            - scene-level rendering helpers

        A scene does not require a camera.
        """

        return self._camera

    @camera.setter
    def camera(
        self,
        value: Node | None,
    ) -> None:
        self.set_camera(
            value
        )

    def set_camera(
        self,
        camera: Node | None,
    ) -> None:
        """
        Assign the primary camera for this scene.

        The camera must belong to the same ECS World as the
        scene.

        Passing None removes the primary camera.
        """

        self._ensure_alive()

        if camera is None:
            self._camera = None
            return

        camera_world = getattr(
            camera,
            "world",
            None,
        )

        if camera_world is not self.world:
            raise ValueError(
                "Camera does not belong to this scene."
            )

        self._camera = camera

    def clear_camera(
        self,
    ) -> None:
        """
        Remove the primary camera from this scene.
        """

        self._ensure_alive()

        self._camera = None

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def enter(
        self,
    ) -> None:
        """
        Activate the scene.

        Called by SceneManager when this scene becomes active.
        """

        self._ensure_alive()

        if (
            self._state
            == SceneState.ACTIVE
        ):
            return

        previous_state = (
            self._state
        )

        self._state = (
            SceneState.ACTIVE
        )

        self.on_enter(
            previous_state
        )

    def exit(
        self,
    ) -> None:
        """
        Deactivate the scene without destroying it.
        """

        self._ensure_alive()

        if (
            self._state
            not in (
                SceneState.ACTIVE,
                SceneState.PAUSED,
            )
        ):
            return

        previous_state = (
            self._state
        )

        self._state = (
            SceneState.INACTIVE
        )

        self.on_exit(
            previous_state
        )

    def pause(
        self,
    ) -> None:
        """
        Pause the active scene.

        A paused scene remains loaded and may still be rendered.
        """

        self._ensure_alive()

        if (
            self._state
            == SceneState.PAUSED
        ):
            return

        if (
            self._state
            != SceneState.ACTIVE
        ):
            raise RuntimeError(
                "Only an active scene can be paused."
            )

        self._state = (
            SceneState.PAUSED
        )

        self.on_pause()

    def resume(
        self,
    ) -> None:
        """
        Resume a paused scene.
        """

        self._ensure_alive()

        if (
            self._state
            == SceneState.ACTIVE
        ):
            return

        if (
            self._state
            != SceneState.PAUSED
        ):
            raise RuntimeError(
                "Only a paused scene can be resumed."
            )

        self._state = (
            SceneState.ACTIVE
        )

        self.on_resume()

    # ==========================================================
    # LIFECYCLE CALLBACKS
    # ==========================================================

    def on_enter(
        self,
        previous_state: SceneState,
    ) -> None:
        """
        Called when the scene becomes active.

        Override in subclasses.
        """

        pass

    def on_exit(
        self,
        previous_state: SceneState,
    ) -> None:
        """
        Called when the scene stops being active.

        Override in subclasses.
        """

        pass

    def on_pause(
        self,
    ) -> None:
        """
        Called when the scene is paused.

        Override in subclasses.
        """

        pass

    def on_resume(
        self,
    ) -> None:
        """
        Called when the scene resumes from pause.

        Override in subclasses.
        """

        pass

    # ==========================================================
    # NODES
    # ==========================================================

    @property
    def nodes(
        self,
    ) -> tuple[
        Node,
        ...
    ]:
        """
        Return direct children of the scene root.
        """

        return tuple(
            self.root.children
        )

    def create_node(
        self,
        name: str,
        parent: Node | None = None,
        *,
        node_type: type[Node] = Node,
    ) -> Node:
        """
        Create and attach a node to the scene.
        """

        self._ensure_alive()

        if parent is None:
            parent = self.root

        if parent.world is not self.world:
            raise ValueError(
                "Parent node does not belong to this scene."
            )

        node = node_type(
            name,
            self.world,
        )

        parent.add_child(
            node
        )

        return node

    def add_node(
        self,
        node: Node,
        parent: Node | None = None,
    ) -> None:
        """
        Attach an existing node to the scene.
        """

        self._ensure_alive()

        if node.world is not self.world:
            raise ValueError(
                "Node does not belong to this scene."
            )

        if node is self.root:
            raise ValueError(
                "The scene root cannot be added as a child."
            )

        if parent is None:
            parent = self.root

        if parent.world is not self.world:
            raise ValueError(
                "Parent node does not belong to this scene."
            )

        parent.add_child(
            node
        )

    def remove_node(
        self,
        node: Node,
    ) -> None:
        """
        Detach a node from the scene.

        The node itself is not automatically destroyed.
        """

        self._ensure_alive()

        if node.world is not self.world:
            raise ValueError(
                "Node does not belong to this scene."
            )

        if node is self.root:
            raise ValueError(
                "The scene root cannot be removed."
            )

        if node.parent is not None:
            node.parent.remove_child(
                node
            )

    def find(
        self,
        name: str,
    ) -> Node | None:
        """
        Find a node by name.
        """

        self._ensure_alive()

        if self.root.name == name:
            return self.root

        return self.root.find_child(
            name
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        """
        Variable timestep update.

        Only active scenes are updated.
        """

        if (
            self._state
            != SceneState.ACTIVE
        ):
            return

        self.root.update_tree(
            delta_time
        )

        self.world.update(
            delta_time
        )

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:
        """
        Execute one fixed physics/update step.

        PhysicsWorld2D rebuilds its broadphase once before the Node
        physics update.
        """

        if (
            self._state
            != SceneState.ACTIVE
        ):
            return

        # ==========================================================
        # Physics broadphase
        # ==========================================================

        physics_world = (
            get_physics_world(
                self.world
            )
        )

        physics_world.rebuild()

        # ==========================================================
        # Node tree
        # ==========================================================

        self.root.fixed_update_tree(
            fixed_delta_time
        )

        # ==========================================================
        # ECS
        # ==========================================================

        self.world.fixed_update(
            fixed_delta_time
        )
    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        """
        Render ECS systems belonging to this scene.

        Active and paused scenes may render.
        """

        if (
            self._state
            not in (
                SceneState.ACTIVE,
                SceneState.PAUSED,
            )
        ):
            return

        self.world.render(
            interpolation
        )

    def render_nodes(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        """
        Render the scene's node hierarchy.

        Active and paused scenes may render.
        """

        if (
            self._state
            not in (
                SceneState.ACTIVE,
                SceneState.PAUSED,
            )
        ):
            return

        self.root.render_tree(
            renderer,
            interpolation,
        )

    # ==========================================================
    # INPUT
    # ==========================================================

    def update_input(
        self,
        input_manager,
    ) -> None:
        """
        Transfer InputManager state into the scene UI system.

        InputManager uses SDL mouse coordinates:

            top-left = 0, 0

        Nexora UI uses centered coordinates:

            center = 0, 0
        """

        if (
            self._state
            != SceneState.ACTIVE
        ):
            return

        # ------------------------------------------------------
        # Mouse
        # ------------------------------------------------------

        mouse_x, mouse_y = (
            input_manager.mouse_position
        )

        viewport_width = (
            self.ui.size[0]
        )

        viewport_height = (
            self.ui.size[1]
        )

        ui_mouse_x = (
            mouse_x
            - viewport_width / 2.0
        )

        ui_mouse_y = (
            mouse_y
            - viewport_height / 2.0
        )

        wheel_x, wheel_y = (
            input_manager.wheel
        )

        self.ui_input.update_mouse(
            position=(
                ui_mouse_x,
                ui_mouse_y,
            ),
            down=input_manager.mouse_down(
                "left",
            ),
            pressed=input_manager.mouse_pressed(
                "left",
            ),
            released=input_manager.mouse_released(
                "left",
            ),
            wheel_x=wheel_x,
            wheel_y=wheel_y,
        )

        # ------------------------------------------------------
        # Keyboard
        # ------------------------------------------------------

        self.ui_input.update_keyboard(
            keys_down=input_manager.keys_down,
            keys_pressed=input_manager.keys_pressed,
            keys_released=input_manager.keys_released,
        )

        # ------------------------------------------------------
        # Text
        # ------------------------------------------------------

        self.ui_input.update_text_input(
            input_manager.text_input,
        )

        # ------------------------------------------------------
        # UI
        # ------------------------------------------------------

        self.ui.update_input(
            self.ui_input
        )

        # ------------------------------------------------------
        # SDL text input mode
        # ------------------------------------------------------

        focused_node = (
            self.ui.focused_node
        )

        if isinstance(
            focused_node,
            TextInput,
        ):
            input_manager.start_text_input()

        else:
            input_manager.stop_text_input()

    # ==========================================================
    # VALIDATION
    # ==========================================================

    def _ensure_alive(
        self,
    ) -> None:
        if self._destroyed:
            raise RuntimeError(
                f"Scene '{self.name}' has been destroyed."
            )

    # ==========================================================
    # DESTROY
    # ==========================================================

    def destroy(
        self,
    ) -> None:
        """
        Destroy this scene and all owned scene resources.
        """

        if self._destroyed:
            return

        # ------------------------------------------------------
        # Exit first
        # ------------------------------------------------------

        if (
            self._state
            in (
                SceneState.ACTIVE,
                SceneState.PAUSED,
            )
        ):
            self.exit()

        # ------------------------------------------------------
        # Camera
        # ------------------------------------------------------

        self._camera = None

        # ------------------------------------------------------
        # Nodes / UI
        # ------------------------------------------------------

        self.root.destroy()
        self.ui.destroy()

        # ------------------------------------------------------
        # State
        # ------------------------------------------------------

        self._state = (
            SceneState.DESTROYED
        )

        self._destroyed = True