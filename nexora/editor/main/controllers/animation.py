from __future__ import annotations

from nexora.animation import AnimationClip, AnimationFrame, AnimationPlayer
from nexora.editor.commands import AnimationClipCommand, SetPropertyCommand
from nexora.nodes.texture.animated_sprite import AnimatedSprite


class AnimationPanelController:
    """Owns animation preview/edit behavior for the editor bottom dock."""

    def __init__(self, editor) -> None:
        self.editor = editor
        if not hasattr(editor, "_animation_clip_name"):
            editor._animation_clip_name = None

    def update(self, delta_time: float) -> None:
        e = self.editor
        animation_node = self._selected_animation_player()
        if (
            getattr(e, "_bottom_tab", "assets") == "animation"
            and animation_node is not None
            and animation_node.playing
        ):
            animation_node.update(delta_time)
            self._refresh_animation_panel()

    def _selected_animation_player(self):
        e = self.editor
        node = e.selection.selected
        return node if isinstance(node, (AnimationPlayer, AnimatedSprite)) else None

    def _animation_speed_property(self, node) -> str:
        e = self.editor
        return "speed_scale" if isinstance(node, AnimationPlayer) else "animation_speed"

    def _animation_speed(self, node) -> float:
        e = self.editor
        return float(
            node.speed_scale
            if isinstance(node, AnimationPlayer)
            else node.animation_speed
        )

    def _add_animation_clip(self) -> None:
        e = self.editor
        node = self._selected_animation_player()
        if node is None:
            return

        existing = {clip.name for clip in node.animations}
        index = 1
        while f"Animation {index}" in existing:
            index += 1
        name = f"Animation {index}"
        clip = AnimationClip(
            name=name,
            frames=(AnimationFrame(index=0, duration=1.0 / 6.0),),
            loop=True,
        )
        e.commands.execute(AnimationClipCommand(node, clip))
        e.document.mark_dirty()
        e._animation_clip_name = name
        node.play(name, restart=True)
        self._refresh_animation_panel()
        e.status_label.text = f"Created animation: {name}"

    def _refresh_animation_panel(self) -> None:
        e = self.editor
        if not hasattr(e, "animation_list"):
            return

        player = self._selected_animation_player()
        enabled = player is not None
        for control in (
            e.animation_list,
            e.animation_frame_list,
            e.animation_new_button,
            e.animation_play_button,
            e.animation_pause_button,
            e.animation_stop_button,
            e.animation_speed_input,
        ):
            control.enabled = enabled

        if player is None:
            e.animation_list.set_items([])
            e.animation_frame_list.set_items([])
            e.animation_status_label.text = "Select an AnimatedSprite or AnimationPlayer"
            return

        animations = player.animations
        names = [clip.name for clip in animations]
        e.animation_list.set_items(names)
        if not names:
            e._animation_clip_name = None
            e.animation_frame_list.set_items([])
            e.animation_status_label.text = "No animations - click New"
            return

        if e._animation_clip_name not in names:
            e._animation_clip_name = (
                player.current_animation_name
                if player.current_animation_name in names
                else names[0]
            )

        animation_index = names.index(e._animation_clip_name)
        e.animation_list.set_selected_index(animation_index, emit=False)
        clip = player.get_animation(e._animation_clip_name)
        if clip is None:
            e.animation_frame_list.set_items([])
            return

        e.animation_frame_list.set_items(
            [
                f"Frame {index}  |  source {frame.index}  |  "
                f"{frame.duration * 1000.0:.1f} ms"
                for index, frame in enumerate(clip.frames)
            ]
        )
        e.animation_speed_input.set_text(
            f"{self._animation_speed(player):g}",
            emit=False,
        )
        state = "Playing" if player.playing else "Stopped"
        e.animation_status_label.text = (
            f"{clip.name}  |  {clip.frame_count} frames  |  {state}"
        )

    def _on_animation_selected(self, index: int, _label: str | None) -> None:
        e = self.editor
        player = self._selected_animation_player()
        if player is None or not (0 <= index < len(player.animations)):
            return
        e._animation_clip_name = player.animations[index].name
        player.play(e._animation_clip_name, restart=True)
        self._refresh_animation_panel()
        e.status_label.text = f"Preview: {e._animation_clip_name}"

    def _on_animation_speed_submitted(self, text: str) -> None:
        e = self.editor
        player = self._selected_animation_player()
        if player is None:
            return
        try:
            speed = float(str(text).strip().replace(",", "."))
        except ValueError:
            e.status_label.text = "Animation speed must be a number"
            self._refresh_animation_panel()
            return
        if speed <= 0.0:
            e.status_label.text = "Animation speed must be greater than zero"
            self._refresh_animation_panel()
            return
        if speed == self._animation_speed(player):
            return
        property_name = self._animation_speed_property(player)
        e.commands.execute(
            SetPropertyCommand(
                player,
                property_name,
                speed,
                label=f"Set {player.name} Animation Speed",
            )
        )
        e.document.mark_dirty()
        self._refresh_animation_panel()
        e.status_label.text = "Animation speed changed"

    def _play_selected_animation(self) -> None:
        e = self.editor
        player = self._selected_animation_player()
        if player is None or e._animation_clip_name is None:
            return
        player.play(e._animation_clip_name)
        self._refresh_animation_panel()

    def _pause_selected_animation(self) -> None:
        e = self.editor
        player = self._selected_animation_player()
        if player is None:
            return
        player.pause()
        self._refresh_animation_panel()

    def _stop_selected_animation(self) -> None:
        e = self.editor
        player = self._selected_animation_player()
        if player is None:
            return
        player.stop()
        self._refresh_animation_panel()

