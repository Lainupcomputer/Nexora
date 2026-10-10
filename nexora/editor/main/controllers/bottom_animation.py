from __future__ import annotations

from nexora.nodes import Label, ListView, TextInput


class BottomAnimationPanel:
    """Owns the Animation tab UI and layout inside the main editor bottom dock."""

    def __init__(self, editor) -> None:
        self.editor = editor

    def build(self) -> None:
        e = self.editor
        e.animation_list = e.bottom_dock.create_child(
            "AnimationList",
            node_type=ListView,
        )
        e.animation_list.item_height = 30.0
        e.animation_list.spacing = 1.0
        e.animation_list.padding_left = 5.0
        e.animation_list.padding_right = 5.0
        e.animation_list.padding_top = 5.0
        e.animation_list.padding_bottom = 5.0
        e.animation_list.text_padding_left = 7.0
        e.animation_list.text_scale = 0.58
        e.animation_list.on_change = e._on_animation_selected

        e.animation_frame_list = e.bottom_dock.create_child(
            "AnimationFrameList",
            node_type=ListView,
        )
        e.animation_frame_list.item_height = 30.0
        e.animation_frame_list.spacing = 1.0
        e.animation_frame_list.padding_left = 5.0
        e.animation_frame_list.padding_right = 5.0
        e.animation_frame_list.padding_top = 5.0
        e.animation_frame_list.padding_bottom = 5.0
        e.animation_frame_list.text_padding_left = 7.0
        e.animation_frame_list.text_scale = 0.58

        e.animation_new_button = e._button(
            e.bottom_dock,
            "AnimationNew",
            "New",
            e._add_animation_clip,
        )

        e.animation_status_label = e.bottom_dock.create_child(
            "AnimationStatus",
            node_type=Label,
        )
        e.animation_status_label.scale = 0.58
        e.animation_status_label.anchor = (0.0, 0.0)
        e.animation_status_label.pivot = (0.0, 0.0)

        e.animation_play_button = e._button(
            e.bottom_dock,
            "AnimationPlay",
            "Play",
            e._play_selected_animation,
        )
        e.animation_pause_button = e._button(
            e.bottom_dock,
            "AnimationPause",
            "Pause",
            e._pause_selected_animation,
        )
        e.animation_stop_button = e._button(
            e.bottom_dock,
            "AnimationStop",
            "Stop",
            e._stop_selected_animation,
        )

        e.animation_speed_input = e.bottom_dock.create_child(
            "AnimationSpeed",
            node_type=TextInput,
        )
        e.animation_speed_input.placeholder = "Speed"
        e.animation_speed_input.auto_size = False
        e.animation_speed_input.on_submit = e._on_animation_speed_submitted

    def set_visible(self, visible: bool) -> None:
        e = self.editor
        for node in (
            e.animation_list,
            e.animation_frame_list,
            e.animation_new_button,
            e.animation_status_label,
            e.animation_play_button,
            e.animation_pause_button,
            e.animation_stop_button,
            e.animation_speed_input,
        ):
            node.visible = visible

    def sync_layout(self, width: float, height: float) -> None:
        e = self.editor
        content_bottom_margin = 8.0
        animation_list_width = min(230.0, max(170.0, width * 0.18))
        animation_top = 70.0
        animation_height = max(
            0.0,
            height - animation_top - content_bottom_margin,
        )
        animation_frame_width = max(
            240.0,
            width - animation_list_width - 28.0,
        )

        e.animation_list.size = (animation_list_width, animation_height)
        e.animation_list.anchor = (0.0, 0.0)
        e.animation_list.pivot = (0.5, 0.5)
        e.animation_list.position = (
            8.0 + animation_list_width / 2.0,
            animation_top + animation_height / 2.0,
        )

        e.animation_frame_list.size = (
            animation_frame_width,
            animation_height,
        )
        e.animation_frame_list.anchor = (0.0, 0.0)
        e.animation_frame_list.pivot = (0.5, 0.5)
        e.animation_frame_list.position = (
            16.0 + animation_list_width + animation_frame_width / 2.0,
            animation_top + animation_height / 2.0,
        )

        e.animation_status_label.position = (
            16.0 + animation_list_width,
            52.0,
        )

        animation_button_y = 49.0
        e.animation_new_button.size = (58.0, 28.0)
        e.animation_new_button.anchor = (0.0, 0.0)
        e.animation_new_button.pivot = (0.5, 0.5)
        e.animation_new_button.position = (37.0, animation_button_y)

        animation_button_x = width - 246.0
        for button, button_width in (
            (e.animation_play_button, 64.0),
            (e.animation_pause_button, 70.0),
            (e.animation_stop_button, 64.0),
        ):
            button.size = (button_width, 28.0)
            button.anchor = (0.0, 0.0)
            button.pivot = (0.5, 0.5)
            button.position = (
                animation_button_x + button_width / 2.0,
                animation_button_y,
            )
            animation_button_x += button_width + 5.0

        e.animation_speed_input.size = (70.0, 28.0)
        e.animation_speed_input.anchor = (1.0, 0.0)
        e.animation_speed_input.pivot = (0.5, 0.5)
        e.animation_speed_input.position = (
            width - 42.0,
            animation_button_y,
        )
