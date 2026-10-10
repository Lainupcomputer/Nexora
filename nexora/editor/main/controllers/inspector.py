from __future__ import annotations

from nexora.editor.commands import SetPropertyCommand
from nexora.editor.inspector import (
    PropertyPathAccessor,
    create_default_inspector_registry,
)
from nexora.nodes import CheckBox, Label, TextInput
from nexora.nodes.node import Node
from nexora.nodes.ui.containers.scroll_view import ScrollView


class InspectorController:
    """Owns Inspector UI, property editing, and Inspector layout."""

    def __init__(self, scene) -> None:
        self.scene = scene
        self.registry = create_default_inspector_registry(Node)
        self.controls: dict[str, object] = {}
        self.labels: dict[str, Label] = {}
        self.groups: dict[str, Label] = {}
        self.syncing = False

    def build(self) -> None:
        scene = self.scene
        scene.inspector_title = scene._panel_title(scene.inspector, "Inspector")

        scene.inspector_type = scene.inspector.create_child(
            "InspectorType",
            node_type=Label,
        )
        scene.inspector_type.text = "No node selected"
        scene.inspector_type.scale = 0.64
        scene.inspector_type.anchor = (0.0, 0.0)
        scene.inspector_type.pivot = (0.0, 0.0)

        scene.inspector_scroll = scene.inspector.create_child(
            "InspectorScroll",
            node_type=ScrollView,
        )
        scene.inspector_scroll.background = (0, 0, 0, 0)
        scene.inspector_scroll.border_width = 0.0
        scene.inspector_scroll.scroll_speed = 48.0

        self.ensure_controls(
            self.registry.registered_properties()
        )
        self.refresh()

    def ensure_controls(self, properties) -> None:
        scene = self.scene

        for prop in properties:
            if prop.group not in self.groups:
                group_label = scene.inspector_scroll.create_content_child(
                    f"InspectorGroup{prop.group.replace(' ', '')}",
                    node_type=Label,
                )
                group_label.text = prop.group
                group_label.scale = 0.68
                group_label.anchor = (0.0, 0.0)
                group_label.pivot = (0.0, 0.0)
                group_label.visible = False
                self.groups[prop.group] = group_label

            if prop.key in self.controls:
                continue

            label = scene.inspector_scroll.create_content_child(
                f"InspectorLabel{prop.key}",
                node_type=Label,
            )
            label.text = prop.label
            label.scale = 0.60
            label.anchor = (0.0, 0.0)
            label.pivot = (0.0, 0.0)
            label.visible = False
            self.labels[prop.key] = label

            if prop.kind == "bool":
                control = scene.inspector_scroll.create_content_child(
                    f"InspectorField{prop.key}",
                    node_type=CheckBox,
                )
                control.text = ""
                control.text_scale = 0.60
                control.box_size = 24.0
                control.on_change = (
                    lambda checked, key=prop.key:
                    self.on_bool_changed(key, checked)
                )
            else:
                control = scene.inspector_scroll.create_content_child(
                    f"InspectorField{prop.key}",
                    node_type=TextInput,
                )
                control.auto_size = False
                control.on_submit = (
                    lambda text, key=prop.key:
                    self.on_text_submitted(key, text)
                )

            control.visible = False
            control.enabled = False
            self.controls[prop.key] = control

    def selected_properties(self):
        node = self.scene.selection.selected
        if node is None:
            return ()
        return self.registry.properties_for(node)

    def property_by_key(self, key: str):
        for prop in self.selected_properties():
            if prop.key == key:
                return prop
        return None

    def refresh(self) -> None:
        scene = self.scene
        node = scene.selection.selected
        self.syncing = True

        try:
            if node is None:
                scene.inspector_type.text = "No node selected"
                for label in self.labels.values():
                    label.visible = False
                for group in self.groups.values():
                    group.visible = False
                for control in self.controls.values():
                    control.visible = False
                    control.enabled = False
                return

            scene.inspector_type.text = (
                f"{type(node).__name__}  |  "
                f"{len(getattr(node, 'children', ()))} child(ren)"
            )

            props = self.registry.properties_for(node)
            self.ensure_controls(props)

            active_keys = {prop.key for prop in props}
            active_groups = {prop.group for prop in props}

            for group in self.groups.values():
                group.visible = False
            for label in self.labels.values():
                label.visible = False
            for control in self.controls.values():
                control.visible = False
                control.enabled = False

            for name, group in self.groups.items():
                group.visible = name in active_groups
            for key, label in self.labels.items():
                label.visible = key in active_keys

            structural_root = (
                node is scene.document.scene.root
                or node is scene.document.scene.ui
            )

            for prop in props:
                control = self.controls.get(prop.key)
                if control is None:
                    continue

                try:
                    value = PropertyPathAccessor(node, prop.path).get()
                except (AttributeError, TypeError):
                    control.visible = False
                    control.enabled = False
                    label = self.labels.get(prop.key)
                    if label is not None:
                        label.visible = False
                    continue

                control.visible = True
                control.enabled = bool(prop.editable)

                if prop.key == "name" and structural_root:
                    control.enabled = False

                if prop.kind == "bool":
                    control.set_checked(bool(value), emit=False)
                elif prop.kind == "float":
                    try:
                        text_value = f"{float(value):.{prop.decimals}f}"
                    except (TypeError, ValueError):
                        text_value = str(value)
                    control.set_text(text_value, emit=False)
                elif prop.kind == "int":
                    try:
                        text_value = str(int(value))
                    except (TypeError, ValueError):
                        text_value = str(value)
                    control.set_text(text_value, emit=False)
                else:
                    control.set_text(str(value), emit=False)
        finally:
            self.syncing = False

    @staticmethod
    def parse_value(prop, text: str):
        if prop.kind == "float":
            value = str(text).strip().replace(",", ".")
            if not value:
                raise ValueError(f"{prop.label} cannot be empty.")
            return float(value)

        if prop.kind == "int":
            value = str(text).strip()
            if not value:
                raise ValueError(f"{prop.label} cannot be empty.")
            return int(value, 0)

        value = str(text)
        if prop.key == "name" and not value.strip():
            raise ValueError("Node name cannot be empty.")
        if prop.key == "name":
            return value.strip()
        return value

    def apply_property(self, prop, value) -> None:
        scene = self.scene
        node = scene.selection.selected
        if node is None:
            return

        if (
            prop.key == "name"
            and (
                node is scene.document.scene.root
                or node is scene.document.scene.ui
            )
        ):
            self.refresh()
            return

        accessor = PropertyPathAccessor(node, prop.path)
        try:
            current = accessor.get()
        except (AttributeError, TypeError) as exc:
            scene._show_error(f"Could not read {prop.label}:\n{exc}")
            return

        if current == value:
            self.refresh()
            return

        try:
            scene.commands.execute(
                SetPropertyCommand(
                    node,
                    prop.path,
                    value,
                    label=(
                        f"Set {getattr(node, 'name', type(node).__name__)} "
                        f"{prop.label}"
                    ),
                )
            )
        except Exception as exc:
            scene._show_error(f"Could not set {prop.label}:\n{exc}")
            self.refresh()
            return

        scene._sync_prefab_instance_overrides(node)
        scene.document.mark_dirty()

        if prop.key == "name":
            scene._refresh_scene_tree()

        self.refresh()
        scene.document_label.text = (
            f"{scene.project.name}  |  {scene.document.title}"
        )
        scene.status_label.text = f"Changed {prop.label}"

    def on_text_submitted(self, key: str, text: str) -> None:
        if self.syncing:
            return

        prop = self.property_by_key(key)
        if prop is None:
            return

        try:
            value = self.parse_value(prop, text)
        except ValueError as exc:
            self.scene.status_label.text = str(exc)
            self.refresh()
            return

        self.apply_property(prop, value)

    def on_bool_changed(self, key: str, checked: bool) -> None:
        if self.syncing:
            return

        prop = self.property_by_key(key)
        if prop is None:
            return

        self.apply_property(prop, bool(checked))

    def on_selection_changed(self) -> None:
        self.refresh()
        scene = self.scene
        if hasattr(scene, "inspector_scroll"):
            self.sync_layout(
                float(scene.inspector.size[0]),
                float(scene.inspector.size[1]),
            )
            scene.inspector_scroll.set_scroll_y(0.0, emit=False)

    def sync_layout(self, width: float, height: float) -> None:
        scene = self.scene
        scene.inspector_title.position = (12.0, 10.0)
        scene.inspector_type.position = (12.0, 39.0)

        scroll_top = 68.0
        scroll_margin = 6.0
        scroll_width = max(0.0, width - scroll_margin * 2.0)
        scroll_height = max(0.0, height - scroll_top - scroll_margin)

        scene.inspector_scroll.anchor = (0.5, 0.0)
        scene.inspector_scroll.pivot = (0.5, 0.5)
        scene.inspector_scroll.size = (scroll_width, scroll_height)
        scene.inspector_scroll.position = (
            0.0,
            scroll_top + scroll_height / 2.0,
        )

        label_x = 8.0
        field_x = max(104.0, scroll_width * 0.40)
        field_right_padding = 14.0
        field_width = max(
            82.0,
            scroll_width - field_x - field_right_padding,
        )

        y = 8.0
        current_group = None

        for prop in self.selected_properties():
            label = self.labels.get(prop.key)
            control = self.controls.get(prop.key)
            if (
                label is None
                or control is None
                or not label.visible
                or not control.visible
            ):
                continue

            if prop.group != current_group:
                current_group = prop.group
                group = self.groups.get(current_group)
                if group is not None and group.visible:
                    group.position = (8.0, y)
                    y += 28.0

            label.position = (label_x, y + 9.0)
            control.anchor = (0.0, 0.0)
            control.pivot = (0.5, 0.5)

            if prop.kind == "bool":
                checkbox_size = 26.0
                control.size = (checkbox_size, checkbox_size)
                control.position = (
                    field_x + checkbox_size / 2.0,
                    y + 15.0,
                )
            else:
                control.size = (field_width, 34.0)
                control.position = (
                    field_x + field_width / 2.0,
                    y + 17.0,
                )

            y += 40.0

        content_height = max(scroll_height, y + 12.0)
        scene.inspector_scroll.set_content_size(
            scroll_width,
            content_height,
        )


__all__ = ["InspectorController"]
