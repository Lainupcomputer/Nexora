from __future__ import annotations

from typing import TYPE_CHECKING

from nexora.nodes import Label
from nexora.editor.commands import TransformNodeCommand, TransformSnapshot
from nexora.editor.main.viewport import (
    EditorViewportCanvas,
    GIZMO_MOVE,
    GIZMO_ROTATE,
    GIZMO_SCALE,
    drag_angle_degrees,
    gizmo_hit_test,
    node_hit_distance,
    world_delta_to_local,
)

if TYPE_CHECKING:
    from nexora.editor.main.scene import EditorScene


class ViewportController:
    """Own viewport UI, navigation, picking, and transform-gizmo workflow."""

    def __init__(self, editor: "EditorScene") -> None:
        self.editor = editor

    def build_viewport(self) -> None:
        editor = self.editor
        # The canvas is created first so it renders above the viewport panel
        # background but below the viewport title / toolbar labels.
        editor.viewport_canvas = editor.viewport.create_child(
            "ViewportCanvas",
            node_type=EditorViewportCanvas,
        )
        editor.viewport_canvas.editor_scene = editor

        editor.viewport_title = editor._panel_title(
            editor.viewport,
            "2D Viewport",
        )

        editor.viewport_hint = editor.viewport.create_child(
            "ViewportHint",
            node_type=Label,
        )
        editor.viewport_hint.text = "World origin"
        editor.viewport_hint.scale = 0.58
        editor.viewport_hint.anchor = (0.5, 0.5)
        editor.viewport_hint.pivot = (0.5, 0.5)

        editor.viewport_subtitle = editor.viewport.create_child(
            "ViewportSubtitle",
            node_type=Label,
        )
        editor.viewport_subtitle.scale = 0.62
        editor.viewport_subtitle.anchor = (0.0, 0.0)
        editor.viewport_subtitle.pivot = (0.0, 0.0)

        editor.viewport_controls = editor.viewport.create_child(
            "ViewportControls",
            node_type=Label,
        )
        editor.viewport_controls.scale = 0.56
        editor.viewport_controls.anchor = (1.0, 0.0)
        editor.viewport_controls.pivot = (1.0, 0.0)

    def viewport_mouse_centered(self) -> tuple[float, float]:
        editor = self.editor
        mouse_x, mouse_y = editor.game.input.mouse_position
        renderer = editor.game.renderer
        if renderer is None:
            return 0.0, 0.0
        return (
            float(mouse_x) - float(renderer.width) * 0.5,
            float(mouse_y) - float(renderer.height) * 0.5,
        )

    def mouse_inside_viewport_canvas(self) -> bool:
        editor = self.editor
        if not hasattr(editor, "viewport_canvas"):
            return False
        mouse_x, mouse_y = editor._viewport_mouse_centered()
        return editor.viewport_canvas.contains_point(
            mouse_x,
            mouse_y,
        )

    def iter_viewport_nodes(self):
        editor = self.editor
        def walk(node):
            for child in tuple(getattr(node, "children", ())):
                yield from walk(child)
                yield child

        yield from walk(editor.document.scene.root)

    def select_node_from_viewport(self) -> None:
        editor = self.editor
        if not editor._mouse_inside_viewport_canvas():
            return

        mouse_x, mouse_y = editor._viewport_mouse_centered()
        center_x, center_y = editor.viewport_canvas.calculate_position()

        best_node = None
        best_distance = None

        for node in editor._iter_viewport_nodes():
            distance = node_hit_distance(
                node,
                mouse_x=mouse_x,
                mouse_y=mouse_y,
                state=editor.viewport_state,
                center_x=center_x,
                center_y=center_y,
            )

            if distance is None:
                continue

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_node = node
                best_distance = distance

        if best_node is None:
            editor.selection.clear()
        else:
            editor.selection.select(best_node)

        editor._refresh_scene_tree()

    def focus_selected_node(self) -> None:
        editor = self.editor
        node = editor._selected_viewport_node()
        if node is None:
            editor.status_label.text = "Select a node to focus"
            return

        try:
            world_x, world_y = node.world_position
        except Exception:
            editor.status_label.text = "Selected node has no world position"
            return

        editor.viewport_state.x = float(world_x)
        editor.viewport_state.y = float(world_y)
        editor.status_label.text = f"Focused {node.name}"

    def selected_viewport_node(self):
        editor = self.editor
        node = editor.selection.selected

        if (
            node is None
            or node is editor.document.scene.root
            or node is editor.document.scene.ui
        ):
            return None

        return node

    def gizmo_pivot_screen(
        self,
        node,
    ) -> tuple[float, float]:
        editor = self.editor
        world_x, world_y = (
            node.world_position
        )

        center_x, center_y = (
            editor.viewport_canvas.calculate_position()
        )

        return editor.viewport_state.world_to_screen(
            world_x,
            world_y,
            center_x,
            center_y,
        )

    def begin_gizmo_drag(
        self,
        node,
        handle: str,
        mouse_x: float,
        mouse_y: float,
    ) -> None:
        editor = self.editor
        pivot_x, pivot_y = (
            editor._gizmo_pivot_screen(
                node
            )
        )

        center_x, center_y = (
            editor.viewport_canvas.calculate_position()
        )

        mouse_world = (
            editor.viewport_state.screen_to_world(
                mouse_x,
                mouse_y,
                center_x,
                center_y,
            )
        )

        editor._gizmo_drag = {
            "node": node,
            "mode": editor.viewport_tool,
            "handle": handle,
            "before": TransformSnapshot.from_node(
                node
            ),
            "start_mouse_x": float(
                mouse_x
            ),
            "start_mouse_y": float(
                mouse_y
            ),
            "start_world_x": float(
                mouse_world[0]
            ),
            "start_world_y": float(
                mouse_world[1]
            ),
            "pivot_x": float(
                pivot_x
            ),
            "pivot_y": float(
                pivot_y
            ),
            "start_angle": drag_angle_degrees(
                mouse_x,
                mouse_y,
                pivot_x,
                pivot_y,
            ),
        }

        editor._gizmo_active_handle = (
            handle
        )

    def update_gizmo_drag(
        self,
        mouse_x: float,
        mouse_y: float,
    ) -> None:
        editor = self.editor
        drag = editor._gizmo_drag

        if drag is None:
            return

        node = drag["node"]

        if not editor.document.scene.world.is_alive(
            node.entity
        ):
            editor._gizmo_drag = None
            editor._gizmo_active_handle = None
            return

        before = drag["before"]
        handle = drag["handle"]
        mode = drag["mode"]

        if mode == GIZMO_MOVE:
            screen_dx = (
                float(mouse_x)
                - drag["start_mouse_x"]
            )

            screen_dy = (
                float(mouse_y)
                - drag["start_mouse_y"]
            )

            world_dx = (
                screen_dx
                / max(
                    editor.viewport_state.zoom,
                    1e-9,
                )
            )

            world_dy = (
                screen_dy
                / max(
                    editor.viewport_state.zoom,
                    1e-9,
                )
            )

            if handle == "x":
                world_dy = 0.0

            elif handle == "y":
                world_dx = 0.0

            local_dx, local_dy = (
                world_delta_to_local(
                    node,
                    world_dx,
                    world_dy,
                )
            )

            x = before.x + local_dx
            y = before.y + local_dy

            if editor.viewport_snap_enabled:
                if handle in {
                    "x",
                    "xy",
                }:
                    x = editor._snap_value(
                        x,
                        editor.viewport_move_snap,
                    )

                if handle in {
                    "y",
                    "xy",
                }:
                    y = editor._snap_value(
                        y,
                        editor.viewport_move_snap,
                    )

            node.transform.x = float(
                x
            )
            node.transform.y = float(
                y
            )

        elif mode == GIZMO_ROTATE:
            current_angle = (
                drag_angle_degrees(
                    mouse_x,
                    mouse_y,
                    drag["pivot_x"],
                    drag["pivot_y"],
                )
            )

            delta = (
                current_angle
                - drag["start_angle"]
            )

            rotation = (
                before.rotation
                + delta
            )

            if editor.viewport_snap_enabled:
                rotation = editor._snap_value(
                    rotation,
                    editor.viewport_rotate_snap,
                )

            node.transform.rotation = float(
                rotation
            )

        elif mode == GIZMO_SCALE:
            dx = (
                float(mouse_x)
                - drag["start_mouse_x"]
            )

            dy = (
                float(mouse_y)
                - drag["start_mouse_y"]
            )

            sensitivity = 90.0

            scale_x = before.scale_x
            scale_y = before.scale_y

            if handle == "x":
                scale_x = (
                    before.scale_x
                    + dx / sensitivity
                )

            elif handle == "y":
                scale_y = (
                    before.scale_y
                    + dy / sensitivity
                )

            else:
                uniform_delta = (
                    dx + dy
                ) / (
                    sensitivity * 2.0
                )

                scale_x = (
                    before.scale_x
                    + uniform_delta
                )

                scale_y = (
                    before.scale_y
                    + uniform_delta
                )

            # Keep the first editor scale tool predictable. Negative scale /
            # sprite flipping can still be entered explicitly in Inspector.
            scale_x = max(
                0.01,
                float(scale_x),
            )

            scale_y = max(
                0.01,
                float(scale_y),
            )

            if editor.viewport_snap_enabled:
                if handle in {
                    "x",
                    "uniform",
                }:
                    scale_x = editor._snap_value(
                        scale_x,
                        editor.viewport_scale_snap,
                    )

                if handle in {
                    "y",
                    "uniform",
                }:
                    scale_y = editor._snap_value(
                        scale_y,
                        editor.viewport_scale_snap,
                    )

                scale_x = max(
                    0.01,
                    scale_x,
                )

                scale_y = max(
                    0.01,
                    scale_y,
                )

            node.transform.scale_x = float(
                scale_x
            )
            node.transform.scale_y = float(
                scale_y
            )

        editor.document.mark_dirty()
        editor._refresh_inspector()
        editor.document_label.text = (
            f"{editor.project.name}  |  "
            f"{editor.document.title}"
        )

    def finish_gizmo_drag(
        self,
        *,
        cancel: bool = False,
    ) -> None:
        editor = self.editor
        drag = editor._gizmo_drag

        if drag is None:
            return

        node = drag["node"]
        before = drag["before"]

        editor._gizmo_drag = None
        editor._gizmo_active_handle = None

        if cancel:
            before.apply(
                node
            )

            editor._refresh_inspector()
            editor.status_label.text = (
                "Transform cancelled"
            )

            return

        after = TransformSnapshot.from_node(
            node
        )

        if after == before:
            return

        mode = drag["mode"]

        label = {
            GIZMO_MOVE: "Move Node",
            GIZMO_ROTATE: "Rotate Node",
            GIZMO_SCALE: "Scale Node",
        }.get(
            mode,
            "Transform Node",
        )

        # The node is already at `after` from live dragging. execute() simply
        # reapplies that value and records exactly one undo/redo operation.
        editor.commands.execute(
            TransformNodeCommand(
                node,
                before,
                after,
                label=label,
            )
        )

        editor._sync_prefab_instance_overrides(node)
        editor.document.mark_dirty()
        editor._refresh_document_ui()
        editor.status_label.text = (
            label
        )

    def gizmo_handle_under_mouse(
        self,
        node,
        mouse_x: float,
        mouse_y: float,
    ) -> str | None:
        editor = self.editor
        pivot_x, pivot_y = (
            editor._gizmo_pivot_screen(
                node
            )
        )

        return gizmo_hit_test(
            editor.viewport_tool,
            mouse_x=mouse_x,
            mouse_y=mouse_y,
            pivot_x=pivot_x,
            pivot_y=pivot_y,
        )

    def update_viewport_input(self) -> None:
        editor = self.editor
        if editor.game.renderer is None:
            return

        if editor._any_editor_dialog_open():
            return

        if editor._asset_drag_active:
            return

        input_manager = editor.game.input

        # Finish a drag even if the pointer leaves the viewport.
        if editor._gizmo_drag is not None:
            mouse_x, mouse_y = (
                editor._viewport_mouse_centered()
            )

            if input_manager.key_pressed(
                "escape"
            ):
                editor._finish_gizmo_drag(
                    cancel=True
                )
                return

            if input_manager.mouse_down(
                "left"
            ):
                editor._update_gizmo_drag(
                    mouse_x,
                    mouse_y,
                )

            if input_manager.mouse_released(
                "left"
            ):
                editor._finish_gizmo_drag()

            return

        if input_manager.key_pressed("f"):
            editor._focus_selected_node()

        if input_manager.key_pressed("home"):
            editor.viewport_state.reset()
            editor.status_label.text = "Viewport reset"

        if not editor._mouse_inside_viewport_canvas():
            editor._gizmo_active_handle = None
            return

        center_x, center_y = (
            editor.viewport_canvas.calculate_position()
        )

        mouse_x, mouse_y = (
            editor._viewport_mouse_centered()
        )

        # ------------------------------------------------------
        # TOOL SHORTCUTS
        # ------------------------------------------------------

        if input_manager.key_pressed(
            "w"
        ):
            editor.viewport_tool = (
                GIZMO_MOVE
            )

        if input_manager.key_pressed(
            "e"
        ):
            editor.viewport_tool = (
                GIZMO_ROTATE
            )

        if input_manager.key_pressed(
            "r"
        ):
            editor.viewport_tool = (
                GIZMO_SCALE
            )

        if input_manager.key_pressed(
            "g"
        ):
            editor.viewport_snap_enabled = (
                not editor.viewport_snap_enabled
            )

        # ------------------------------------------------------
        # CAMERA
        # ------------------------------------------------------

        if input_manager.mouse_down(
            "middle"
        ):
            delta_x, delta_y = (
                input_manager.mouse_delta
            )

            if delta_x or delta_y:
                editor.viewport_state.pan_screen_delta(
                    delta_x,
                    delta_y,
                )

        _wheel_x, wheel_y = (
            input_manager.wheel
        )

        if wheel_y:
            factor = (
                1.15
                ** float(wheel_y)
            )

            editor.viewport_state.zoom_at(
                mouse_x,
                mouse_y,
                center_x,
                center_y,
                factor,
            )

        # ------------------------------------------------------
        # GIZMO
        # ------------------------------------------------------

        selected = (
            editor._selected_viewport_node()
        )

        handle = None

        if selected is not None:
            handle = (
                editor._gizmo_handle_under_mouse(
                    selected,
                    mouse_x,
                    mouse_y,
                )
            )

        editor._gizmo_active_handle = (
            handle
        )

        if (
            input_manager.mouse_pressed(
                "left"
            )
            and not input_manager.mouse_down(
                "middle"
            )
        ):
            if (
                selected is not None
                and handle is not None
            ):
                editor._begin_gizmo_drag(
                    selected,
                    handle,
                    mouse_x,
                    mouse_y,
                )

            else:
                editor._select_node_from_viewport()

        snap_text = (
            "ON"
            if editor.viewport_snap_enabled
            else "OFF"
        )

        tool_text = {
            GIZMO_MOVE: "Move",
            GIZMO_ROTATE: "Rotate",
            GIZMO_SCALE: "Scale",
        }.get(
            editor.viewport_tool,
            editor.viewport_tool,
        )

        editor.viewport_controls.text = (
            f"W Move  E Rotate  R Scale  G Snap:{snap_text}   "
            f"F Focus  Home Reset  P Paint  X Erase  B Fill  "
            f"MMB Pan  Wheel Zoom   "
            f"{tool_text}   "
            f"{editor.viewport_state.zoom * 100.0:.0f}%"
        )

    def sync_viewport_layout(self, width: float, height: float) -> None:
        editor = self.editor
        editor.viewport_title.position = (12.0, 10.0)

        header_height = 74.0
        margin = 5.0
        canvas_width = max(0.0, width - margin * 2.0)
        canvas_height = max(0.0, height - header_height - margin)

        editor.viewport_canvas.anchor = (0.5, 0.0)
        editor.viewport_canvas.pivot = (0.5, 0.5)
        editor.viewport_canvas.size = (
            canvas_width,
            canvas_height,
        )
        editor.viewport_canvas.position = (
            0.0,
            header_height + canvas_height / 2.0,
        )

        editor.viewport_hint.position = (0.0, 0.0)

        editor.viewport_subtitle.text = (
            f"Editing: {editor.document.display_name}"
        )
        editor.viewport_subtitle.position = (
            118.0,
            11.0,
        )

        snap_text = (
            "ON"
            if editor.viewport_snap_enabled
            else "OFF"
        )

        tool_text = {
            GIZMO_MOVE: "Move",
            GIZMO_ROTATE: "Rotate",
            GIZMO_SCALE: "Scale",
        }.get(
            editor.viewport_tool,
            editor.viewport_tool,
        )

        editor.viewport_controls.text = (
            f"W Move  E Rotate  R Scale  G Snap:{snap_text}   "
            f"MMB Pan  Wheel Zoom   "
            f"{tool_text}   "
            f"{editor.viewport_state.zoom * 100.0:.0f}%"
        )
        editor.viewport_controls.position = (
            -12.0,
            11.0,
        )
