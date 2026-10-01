from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

import sdl3

from nexora.audio import AudioSource
from nexora.nodes.effects import Light2D
from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.controls.button import Button
from nexora.nodes.ui.output.label import Label
from nexora.nodes.ui.ui_node import UINode
from nexora.signals import Signal


MAX_DIALOGUE_CHOICES = 4


@dataclass(frozen=True, slots=True)
class DialogueChoice:
    """One selectable answer in a :class:`DialoguePage`.

    ``next_page`` is an optional zero-based index into the page list passed
    to :meth:`DialogueBox.set_pages`.  When it is omitted, the next page in
    the list is opened automatically.

    ``callback`` is called after the choice is selected and before the next
    page opens. It receives the selected choice, so the game can persist
    ``choice.value`` in its save data.
    """

    text: str
    next_page: int | None = None
    value: Any = None
    callback: Callable[["DialogueChoice"], Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("DialogueChoice.text cannot be empty.")

        if self.next_page is not None and not isinstance(
            self.next_page,
            int,
        ):
            raise TypeError("DialogueChoice.next_page must be an int or None.")

        if self.callback is not None and not callable(self.callback):
            raise TypeError("DialogueChoice.callback must be callable or None.")


@dataclass(frozen=True, slots=True)
class DialoguePage:
    """One page of narrative dialogue.

    The portrait is intentionally a texture object instead of an asset path.
    Load it through ``assets.texture(...)`` and pass the returned GPU texture
    here.  This keeps the node independent from the game's asset manager.
    """

    speaker: str
    text: str
    portrait: object | None = None
    choices: tuple[DialogueChoice, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.speaker, str):
            raise TypeError("DialoguePage.speaker must be a string.")

        if not isinstance(self.text, str):
            raise TypeError("DialoguePage.text must be a string.")

        choices = tuple(self.choices)
        if len(choices) > MAX_DIALOGUE_CHOICES:
            raise ValueError(
                "A dialogue page can contain at most "
                f"{MAX_DIALOGUE_CHOICES} choices."
            )

        if any(not isinstance(choice, DialogueChoice) for choice in choices):
            raise TypeError(
                "DialoguePage.choices must contain DialogueChoice objects."
            )

        object.__setattr__(self, "choices", choices)


class _PortraitView(UINode):
    """Small screen-space texture view used by ``DialogueBox``."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)
        self.texture = None
        self.alpha = 1.0
        self.keep_aspect = True

    def render(self, renderer) -> None:
        if not self.visible or self.texture is None:
            return

        x, y = self.calculate_position()
        view_width, view_height = self.size

        texture_width = max(
            1.0,
            float(getattr(self.texture, "width", view_width)),
        )
        texture_height = max(
            1.0,
            float(getattr(self.texture, "height", view_height)),
        )

        if self.keep_aspect:
            scale = min(
                view_width / texture_width,
                view_height / texture_height,
            )
            width = texture_width * max(scale, 0.0)
            height = texture_height * max(scale, 0.0)
        else:
            width = view_width
            height = view_height

        renderer.sprite(
            self.texture,
            x,
            y,
            width=width,
            height=height,
            origin=(0.5, 0.5),
            alpha=max(0.0, min(1.0, float(self.alpha))),
            layer=1,
        )


class _DialogueTextView(UINode):
    """Renders the speaker name and the currently revealed text."""

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.speaker = ""
        self.text = ""
        # Narrative text should be clearly readable at the game's native
        # resolution instead of using the small default UI scale.
        self.text_scale = 1.35
        self.speaker_scale = 0.86
        self.text_alignment = "center"
        self.line_spacing = 4.0
        self.padding = 2.0
        self.continue_hint = "LEERTASTE"
        self.show_continue_hint = False

    @staticmethod
    def _measure(renderer, text: str, scale: float) -> tuple[float, float]:
        if not text:
            return (0.0, 0.0)
        return renderer.text_measure(text, scale=scale)

    @classmethod
    def _wrap_text(
        cls,
        renderer,
        text: str,
        max_width: float,
        scale: float,
    ) -> list[str]:
        """Wrap text without requiring a separate text-layout subsystem."""

        max_width = max(1.0, float(max_width))
        paragraphs = text.split("\n") or [""]
        lines: list[str] = []

        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue

            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                width, _ = cls._measure(renderer, candidate, scale)

                if current and width > max_width:
                    lines.append(current)
                    current = ""

                if not current:
                    word_width, _ = cls._measure(renderer, word, scale)
                    if word_width <= max_width:
                        current = word
                        continue

                    # Hard-wrap a single word that is wider than the box.
                    chunk = ""
                    for character in word:
                        candidate_chunk = f"{chunk}{character}"
                        chunk_width, _ = cls._measure(
                            renderer,
                            candidate_chunk,
                            scale,
                        )
                        if chunk and chunk_width > max_width:
                            lines.append(chunk)
                            chunk = character
                        else:
                            chunk = candidate_chunk
                    current = chunk
                else:
                    current = candidate

            lines.append(current)

        return lines or [""]

    def render(self, renderer) -> None:
        if not self.visible:
            return

        x, y = self.calculate_position()
        width, height = self.size
        left = x - width * self.pivot[0] + self.padding
        top = y - height * self.pivot[1] + self.padding
        content_width = max(1.0, width - self.padding * 2.0)
        content_height = max(1.0, height - self.padding * 2.0)

        baseline = renderer.text_baseline(scale=self.text_scale)
        _, sample_height = self._measure(
            renderer,
            "Ag",
            self.text_scale,
        )
        line_height = max(
            sample_height,
            baseline,
            1.0,
        ) + self.line_spacing

        body_top = top
        body_height = max(1.0, top + content_height - body_top)
        lines = self._wrap_text(
            renderer,
            self.text,
            content_width,
            self.text_scale,
        )

        # Center the complete text block in the available right-hand area.
        # The previous layout only centered each line horizontally, while
        # the first line still started at the very top of the text view.
        text_block_height = max(
            sample_height,
            baseline,
            1.0,
        ) + max(0, len(lines) - 1) * line_height
        text_top = body_top + max(
            0.0,
            (body_height - text_block_height) / 2.0,
        )

        push_clip = getattr(renderer, "push_clip_rect", None)
        pop_clip = getattr(renderer, "pop_clip_rect", None)
        clipped = callable(push_clip) and callable(pop_clip)

        if clipped:
            push_clip(
                left,
                body_top,
                content_width,
                body_height,
            )

        try:
            for index, line in enumerate(lines):
                line_y = text_top + baseline + index * line_height
                if line_y > body_top + body_height + baseline:
                    break
                if line:
                    line_width, _ = self._measure(
                        renderer,
                        line,
                        self.text_scale,
                    )
                    line_x = left
                    if self.text_alignment == "center":
                        line_x = left + max(
                            0.0,
                            (content_width - line_width) / 2.0,
                        )
                    elif self.text_alignment == "right":
                        line_x = left + max(
                            0.0,
                            content_width - line_width,
                        )
                    renderer.text(
                        line,
                        line_x,
                        line_y,
                        scale=self.text_scale,
                    )
        finally:
            if clipped:
                pop_clip()

        if self.show_continue_hint and self.continue_hint:
            hint_width, hint_height = self._measure(
                renderer,
                self.continue_hint,
                0.62,
            )
            renderer.text(
                self.continue_hint,
                left + content_width - hint_width,
                top + content_height - hint_height + baseline,
                scale=0.62,
            )


class _DialogueEffectsView(UINode):
    """Low-cost screen-space portrait light.

    Light2D is a world node in Nexora, while a DialogueBox is rendered in the
    screen-space UI pass.  The light is therefore owned here and advanced
    explicitly; its animated intensity drives a small overlay glow that stays
    attached to the portrait even when the gameplay camera moves.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self._light_position = (0.0, 0.0)

        self._light = Light2D(f"{name}Light", world)
        self._light.color = (1.0, 0.48, 0.14)
        self._light.radius = 92.0
        self._light.intensity = 1.0
        self._light.falloff = 2.0
        self._light.flicker_enabled = True
        self._light.flicker_strength = 0.16
        self._light.flicker_speed = 8.0

        self.visible = False

    def set_positions(
        self,
        *,
        light: tuple[float, float],
    ) -> None:
        self._light_position = (float(light[0]), float(light[1]))

    def start(self) -> None:
        self.visible = True
        self._light.light_enabled = True

    def stop(self) -> None:
        self.visible = False
        self._light.light_enabled = False

    def update(self, delta_time: float) -> None:
        if not self.visible:
            return

        delta_time = max(float(delta_time), 0.0)
        self._light.transform.x, self._light.transform.y = self._light_position
        self._light.update(delta_time)

    def render(self, renderer) -> None:
        if not self.visible:
            return

        x, y = self._light_position
        intensity = max(0.0, min(1.5, self._light.effective_intensity))
        scope_factory = getattr(renderer, "overlay_scope", None)
        scope = scope_factory() if callable(scope_factory) else nullcontext()

        with scope:
            # A few translucent rings make the Light2D flicker readable in
            # the UI overlay, which is rendered after the world lighting pass.
            renderer.circle(
                x,
                y,
                118.0,
                color=(1.0, 0.30, 0.06, 0.025 * intensity),
                layer=1,
            )
            renderer.circle(
                x,
                y,
                78.0,
                color=(1.0, 0.46, 0.10, 0.055 * intensity),
                layer=1,
            )
            renderer.circle(
                x,
                y,
                42.0,
                color=(1.0, 0.70, 0.22, 0.11 * intensity),
                layer=2,
            )

    def destroy(self) -> None:
        # The helper light is intentionally not attached to the UI tree;
        # release its ECS entity when the dialogue is destroyed.
        self._light.destroy()
        super().destroy()


class DialogueBox(UINode):
    """Reusable narrative dialogue UI.

    The node is intended to be created below ``Scene.ui``::

        dialogue = scene.ui.create_child(
            "Dialogue",
            node_type=DialogueBox,
        )
        dialogue.set_pages([
            DialoguePage(
                speaker="Jonas",
                text="Ich muss ihr helfen.",
                portrait=jonas_portrait,
            ),
            DialoguePage(
                speaker="Clara",
                text="Willst du dich mit Clara anfreunden?",
                portrait=clara_portrait,
                choices=(
                    DialogueChoice("Ja", next_page=2),
                    DialogueChoice("Nein", next_page=3),
                ),
            ),
            DialoguePage(
                speaker="Jonas",
                text="Dann lernen wir uns besser kennen.",
            ),
            DialoguePage(
                speaker="Jonas",
                text="Vielleicht ein anderes Mal.",
            ),
        ])
        dialogue.open()

    Text is revealed character by character.  Pressing Space once while a
    page is still typing reveals the complete page; pressing it again opens
    the next page.  Choice pages wait for a click on one of their buttons.
    """

    def __init__(self, name: str, world) -> None:
        super().__init__(name, world)

        self.width_mode = "fill"
        self.height_mode = "fill"
        self.anchor = (0.5, 0.5)
        self.pivot = (0.5, 0.5)

        self.margin = 24.0
        self.panel_width = 1040.0
        self.panel_height = 205.0
        self.panel_padding = 16.0
        self.portrait_size = 146.0
        self.choice_button_height = 34.0
        self.choice_gap = 7.0

        self.characters_per_second = 38.0
        self.dim_background = True

        # Optional UI typing sound.  It is deliberately disabled until the
        # game supplies a loaded Sound through set_typing_sound(...).
        # Keeping one source and restarting it avoids allocating an audio
        # source for every revealed character.
        self.typing_sound_volume = 0.08
        self.typing_sound_interval = 0.07
        self._typing_audio = None
        self._typing_sound = None
        self._typing_source: AudioSource | None = None
        self._typing_sound_cooldown = 0.0

        self.backdrop_color = (0, 0, 0, 92)
        self.window_shadow_color = (0, 0, 0, 145)
        self.window_background = (12, 17, 23, 248)
        self.window_border_color = (206, 151, 73, 255)
        self.window_accent_color = (238, 183, 88, 235)
        self.window_divider_color = (112, 79, 45, 190)
        self.portrait_background = (8, 11, 16, 255)
        self.portrait_border_color = (143, 102, 57, 255)
        self.speaker_badge_background = (27, 35, 41, 245)
        self.speaker_badge_border_color = (143, 102, 57, 235)
        self.choice_background = (20, 29, 36, 242)
        self.choice_hover_background = (53, 68, 70, 248)
        self.choice_focus_background = (42, 56, 62, 248)
        self.choice_border_color = (127, 94, 56, 240)
        self.choice_focus_border_color = (224, 171, 83, 255)

        self.opened = Signal(f"{name}.opened", owner=self)
        self.closed = Signal(f"{name}.closed", owner=self)
        self.page_changed = Signal(f"{name}.page_changed", owner=self)
        self.choice_selected = Signal(f"{name}.choice_selected", owner=self)
        self.finished = Signal(f"{name}.finished", owner=self)

        self.backdrop = self.create_child("Backdrop", node_type=Panel)
        self.backdrop.anchor = (0.5, 0.5)
        self.backdrop.pivot = (0.5, 0.5)
        self.backdrop.border_width = 0.0

        self.window_shadow = self.create_child(
            "WindowShadow",
            node_type=Panel,
        )
        self.window_shadow.anchor = (0.5, 0.5)
        self.window_shadow.pivot = (0.5, 0.5)
        self.window_shadow.border_width = 0.0
        self.window_shadow.background = self.window_shadow_color

        self.window = self.create_child("Window", node_type=Panel)
        self.window.anchor = (0.5, 0.5)
        self.window.pivot = (0.5, 0.5)
        self.window.border_width = 2.0
        self.window.border_radius = 8.0

        # The effect view is inserted before the portrait/text children so
        # the glow sits inside the panel without covering the text.
        self.effects = self.window.create_child(
            "DialogueEffects",
            node_type=_DialogueEffectsView,
        )

        self.top_accent = self.window.create_child(
            "TopAccent",
            node_type=Panel,
        )
        self.top_accent.anchor = (0.5, 0.5)
        self.top_accent.pivot = (0.5, 0.5)
        self.top_accent.border_width = 0.0
        self.top_accent.background = self.window_accent_color
        self.top_accent.border_radius = 1.5

        self.text_divider = self.window.create_child(
            "TextDivider",
            node_type=Panel,
        )
        self.text_divider.anchor = (0.5, 0.5)
        self.text_divider.pivot = (0.5, 0.5)
        self.text_divider.border_width = 0.0
        self.text_divider.background = self.window_divider_color

        self.portrait_frame = self.window.create_child(
            "PortraitFrame",
            node_type=Panel,
        )
        self.portrait_frame.anchor = (0.5, 0.5)
        self.portrait_frame.pivot = (0.5, 0.5)
        self.portrait_frame.border_width = 2.0
        self.portrait_frame.border_radius = 3.0

        self.portrait = self.portrait_frame.create_child(
            "Portrait",
            node_type=_PortraitView,
        )
        self.portrait.anchor = (0.5, 0.5)
        self.portrait.pivot = (0.5, 0.5)

        self.speaker_badge = self.window.create_child(
            "SpeakerBadge",
            node_type=Panel,
        )
        self.speaker_badge.anchor = (0.5, 0.5)
        self.speaker_badge.pivot = (0.5, 0.5)
        self.speaker_badge.background = self.speaker_badge_background
        self.speaker_badge.border_color = self.speaker_badge_border_color
        self.speaker_badge.border_width = 1.0
        self.speaker_badge.border_radius = 4.0

        self.speaker_label = self.speaker_badge.create_child(
            "SpeakerName",
            node_type=Label,
        )
        self.speaker_label.anchor = (0.5, 0.5)
        self.speaker_label.pivot = (0.5, 0.5)
        self.speaker_label.scale = 0.90
        self.speaker_badge.visible = False

        self.text_view = self.window.create_child(
            "Text",
            node_type=_DialogueTextView,
        )
        self.text_view.anchor = (0.5, 0.5)
        self.text_view.pivot = (0.5, 0.5)

        self.choice_panel = self.window.create_child(
            "Choices",
            node_type=Panel,
        )
        self.choice_panel.anchor = (0.5, 0.5)
        self.choice_panel.pivot = (0.5, 0.5)
        self.choice_panel.background = (0, 0, 0, 0)
        self.choice_panel.border_width = 0.0

        self._choice_buttons: list[Button] = []
        for index in range(MAX_DIALOGUE_CHOICES):
            button = self.choice_panel.create_child(
                f"Choice{index + 1}",
                node_type=Button,
            )
            # Choices are deliberately mouse-selectable without stealing
            # Space from the dialogue's global advance key.
            button.focusable = False
            button.on_click = lambda index=index: self.choose(index)
            self._choice_buttons.append(button)

        self.continue_hint_badge = self.window.create_child(
            "ContinueHint",
            node_type=Panel,
        )
        self.continue_hint_badge.anchor = (0.5, 0.5)
        self.continue_hint_badge.pivot = (0.5, 0.5)
        self.continue_hint_badge.border_width = 2.0
        self.continue_hint_badge.border_radius = 5.0

        self.continue_hint_label = self.continue_hint_badge.create_child(
            "ContinueHintLabel",
            node_type=Label,
        )
        self.continue_hint_label.anchor = (0.5, 0.5)
        self.continue_hint_label.pivot = (0.5, 0.5)
        self.continue_hint_label.text = "LEERTASTE  >"
        self.continue_hint_label.scale = 0.72
        self.continue_hint_badge.visible = False

        self._pages: tuple[DialoguePage, ...] = ()
        self._current_page_index = -1
        self._typed_count = 0
        self._typewriter_progress = 0.0
        self._is_open = False

        self.visible = False
        self.enabled = False

        self._apply_style()
        self._sync_layout()

    # ==============================================================
    # Public state
    # ==============================================================

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def pages(self) -> tuple[DialoguePage, ...]:
        return self._pages

    @property
    def current_page_index(self) -> int:
        return self._current_page_index

    @property
    def current_page(self) -> DialoguePage | None:
        if not 0 <= self._current_page_index < len(self._pages):
            return None
        return self._pages[self._current_page_index]

    @property
    def text_finished(self) -> bool:
        page = self.current_page
        return page is None or self._typed_count >= len(page.text)

    # ==============================================================
    # Pages
    # ==============================================================

    @staticmethod
    def _coerce_page(page: DialoguePage | dict[str, Any]) -> DialoguePage:
        if isinstance(page, DialoguePage):
            return page
        if isinstance(page, dict):
            return DialoguePage(**page)
        raise TypeError(
            "Dialogue pages must be DialoguePage objects or dictionaries."
        )

    def set_pages(
        self,
        pages: Iterable[DialoguePage | dict[str, Any]],
    ) -> DialogueBox:
        """Replace the complete sequence of pages."""

        resolved = tuple(self._coerce_page(page) for page in pages)
        if not resolved:
            raise ValueError("DialogueBox requires at least one page.")

        for page in resolved:
            for choice in page.choices:
                if choice.next_page is not None and not (
                    0 <= choice.next_page < len(resolved)
                ):
                    raise ValueError(
                        "DialogueChoice.next_page points outside the page list: "
                        f"{choice.next_page}"
                    )

        self._pages = resolved
        self._current_page_index = -1

        if self._is_open:
            self._show_page(0, emit=True)

        return self

    def append_page(self, page: DialoguePage | dict[str, Any]) -> DialogueBox:
        """Append one page to the current sequence."""

        return self.set_pages((*self._pages, self._coerce_page(page)))

    # ==============================================================
    # Optional typing audio
    # ==============================================================

    def set_typing_sound(
        self,
        audio,
        sound,
        *,
        volume: float = 0.08,
        min_interval: float = 0.07,
    ) -> DialogueBox:
        """Configure the short sound played while text is revealed.

        ``sound`` should be loaded through the game's existing asset/audio
        services, for example::

            typing = assets.sound("audio/dialogue/typing.wav")
            dialogue.set_typing_sound(self.audio, typing)

        The node uses ``audio.player`` and one reusable ``AudioSource``.  It
        never changes the global audio queue settings and silently remains
        disabled when no audio system or sound is supplied.
        """

        volume = float(volume)
        min_interval = float(min_interval)
        if not 0.0 <= volume <= 1.0:
            raise ValueError("Typing sound volume must be between 0.0 and 1.0.")
        if min_interval < 0.0:
            raise ValueError("Typing sound interval cannot be negative.")

        self._stop_typing_sound(remove=True)
        self._typing_audio = audio
        self._typing_sound = sound
        self.typing_sound_volume = volume
        self.typing_sound_interval = min_interval
        self._typing_sound_cooldown = 0.0
        self._typing_source = None
        return self

    def clear_typing_sound(self) -> DialogueBox:
        """Disable and release the optional typing sound."""

        self._stop_typing_sound(remove=True)
        self._typing_audio = None
        self._typing_sound = None
        self._typing_source = None
        self._typing_sound_cooldown = 0.0
        return self

    def _stop_typing_sound(self, *, remove: bool = False) -> None:
        source = self._typing_source
        if source is None:
            return

        player = getattr(self._typing_audio, "player", None)
        try:
            if player is not None:
                player.stop(source)
                if remove:
                    player.remove(source)
            else:
                source.stop()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            # Dialogue audio is optional and must not break a scene when the
            # audio device is already shutting down.
            try:
                source.stop()
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass

    def _play_typing_tick(self) -> None:
        if (
            self._typing_audio is None
            or self._typing_sound is None
            or self._typing_sound_cooldown > 0.0
        ):
            return

        player = getattr(self._typing_audio, "player", None)
        if player is None:
            return

        try:
            if self._typing_source is None:
                self._typing_source = AudioSource(
                    self._typing_sound,
                    bus="SFX",
                    volume=self.typing_sound_volume,
                    loop=False,
                )
            else:
                self._typing_source.volume = self.typing_sound_volume
                self._typing_source.loop = False

            # AudioPlayer.play() restarts this same source from the beginning.
            player.play(self._typing_source)
            self._typing_sound_cooldown = self.typing_sound_interval
        except (AttributeError, RuntimeError, TypeError, ValueError):
            # A missing/unsupported optional sound should not stop dialogue.
            self._typing_source = None

    # ==============================================================
    # Opening / closing
    # ==============================================================

    def open(
        self,
        pages: Iterable[DialoguePage | dict[str, Any]] | None = None,
        *,
        start_page: int = 0,
    ) -> DialogueBox:
        """Open the dialogue and start at ``start_page``."""

        if pages is not None:
            self.set_pages(pages)

        if not self._pages:
            raise ValueError("Set dialogue pages before opening the DialogueBox.")

        if not 0 <= int(start_page) < len(self._pages):
            raise IndexError(f"Dialogue start page out of range: {start_page}")

        root = self.ui_root
        if self._is_open:
            self._show_page(int(start_page), emit=True)
            return self

        self._is_open = True
        self.visible = True
        self.enabled = True

        self.effects.start()

        if root is not None:
            push_modal = getattr(root, "push_modal", None)
            if callable(push_modal):
                push_modal(self)

        self._show_page(int(start_page), emit=True)
        self.opened.emit(self)
        return self

    def start(
        self,
        pages: Iterable[DialoguePage | dict[str, Any]] | None = None,
        *,
        start_page: int = 0,
    ) -> DialogueBox:
        """Readable alias for :meth:`open` when starting a new sequence."""

        return self.open(pages, start_page=start_page)

    def close(self) -> DialogueBox:
        if not self._is_open:
            self._stop_typing_sound()
            return self

        root = self.ui_root
        self._stop_typing_sound()
        self._is_open = False
        self.visible = False
        self.enabled = False
        self.effects.stop()
        self.continue_hint_badge.visible = False

        if root is not None:
            pop_modal = getattr(root, "pop_modal", None)
            if callable(pop_modal):
                pop_modal(self)

        self._hide_choices()
        self.closed.emit(self)
        return self

    # ==============================================================
    # Typewriter / navigation
    # ==============================================================

    def _show_page(self, index: int, *, emit: bool) -> None:
        if not 0 <= index < len(self._pages):
            raise IndexError(f"Dialogue page out of range: {index}")

        self._stop_typing_sound()
        self._typing_sound_cooldown = 0.0
        self._current_page_index = index
        self._typed_count = 0
        self._typewriter_progress = 0.0

        page = self._pages[index]
        self.portrait.texture = page.portrait
        self.speaker_label.text = page.speaker
        self.speaker_badge.visible = bool(page.speaker)
        # The name is rendered below the portrait. The text view only draws
        # the actual dialogue body on the right-hand side.
        self.text_view.speaker = ""
        self.text_view.text = ""
        self.text_view.show_continue_hint = False
        self._sync_layout()

        if emit:
            self.page_changed.emit(self, page, index)

    def _reveal_all(self) -> None:
        page = self.current_page
        if page is None:
            return

        self._stop_typing_sound()
        self._typed_count = len(page.text)
        self._typewriter_progress = float(self._typed_count)
        self.text_view.text = page.text
        self._sync_choices()

    def advance(self) -> None:
        """Reveal the current page or move to the next non-choice page."""

        if not self._is_open:
            return

        if not self.text_finished:
            self._reveal_all()
            return

        page = self.current_page
        if page is None or page.choices:
            return

        next_index = self._current_page_index + 1
        if next_index >= len(self._pages):
            self.finish()
            return

        self._show_page(next_index, emit=True)

    def choose(self, index: int) -> None:
        """Select one visible choice and follow its page target."""

        if not self._is_open or not self.text_finished:
            return

        page = self.current_page
        if page is None or not 0 <= int(index) < len(page.choices):
            return

        index = int(index)
        choice = page.choices[index]
        self.choice_selected.emit(self, choice, index)

        if choice.callback is not None:
            choice.callback(choice)

        # User callbacks may close or replace the dialogue.
        if not self._is_open:
            return

        if choice.next_page is None:
            next_index = self._current_page_index + 1
        else:
            next_index = choice.next_page

        if next_index >= len(self._pages):
            self.finish()
            return

        self._show_page(next_index, emit=True)

    def finish(self) -> None:
        if not self._is_open:
            return

        self.finished.emit(self)
        if self._is_open:
            self.close()

    def update(self, delta_time: float) -> None:
        self._typing_sound_cooldown = max(
            0.0,
            self._typing_sound_cooldown - max(0.0, float(delta_time)),
        )

        if not self._is_open or self.text_finished:
            return

        page = self.current_page
        if page is None:
            return

        speed = max(0.0, float(self.characters_per_second))
        if speed <= 0.0:
            self._reveal_all()
            return

        self._typewriter_progress += max(0.0, float(delta_time)) * speed
        target = min(
            len(page.text),
            int(self._typewriter_progress),
        )

        if target == self._typed_count:
            return

        previous_count = self._typed_count
        self._typed_count = target
        self.text_view.text = page.text[:target]

        newly_revealed = page.text[previous_count:target]
        if any(not character.isspace() for character in newly_revealed):
            self._play_typing_tick()

        if self.text_finished:
            self._stop_typing_sound()
            self._sync_choices()

    # ==============================================================
    # Layout / style
    # ==============================================================

    def _apply_style(self) -> None:
        self.backdrop.background = self.backdrop_color
        self.window.background = self.window_background
        self.window.border_color = self.window_border_color
        self.portrait_frame.background = self.portrait_background
        self.portrait_frame.border_color = self.portrait_border_color
        self.window_shadow.background = self.window_shadow_color
        self.top_accent.background = self.window_accent_color
        self.text_divider.background = self.window_divider_color
        self.speaker_badge.background = self.speaker_badge_background
        self.speaker_badge.border_color = self.speaker_badge_border_color
        self.continue_hint_badge.background = (132, 89, 30, 248)
        self.continue_hint_badge.border_color = self.window_accent_color
        self.continue_hint_label.scale = 0.72

        for button in self._choice_buttons:
            button.normal_background = self.choice_background
            button.hover_background = self.choice_hover_background
            button.focus_background = self.choice_focus_background
            button.pressed_background = self.choice_background
            button.normal_border_color = self.choice_border_color
            button.focus_border_color = self.choice_focus_border_color
            button.normal_border_width = 1.0
            button.focus_border_width = 2.0
            button.text_scale = 0.78

    def _hide_choices(self) -> None:
        for button in self._choice_buttons:
            button.visible = False
            button.enabled = False
            button.text = ""

        self.choice_panel.visible = False

    def _sync_choices(self) -> None:
        page = self.current_page
        choices = () if page is None else page.choices
        ready = self.text_finished

        for index, button in enumerate(self._choice_buttons):
            if index >= len(choices):
                button.visible = False
                button.enabled = False
                button.text = ""
                continue

            button.text = choices[index].text
            button.visible = True
            button.enabled = ready

        self.choice_panel.visible = bool(choices)
        # The old plain text hint is kept disabled.  The badge is much easier
        # to notice and does not compete with the body text.
        self.text_view.show_continue_hint = False
        self.continue_hint_badge.visible = (
            self._is_open
            and ready
            and not choices
        )

    def _sync_layout(self) -> None:
        viewport_width = max(1.0, float(self._viewport_width))
        viewport_height = max(1.0, float(self._viewport_height))
        self.size = (viewport_width, viewport_height)

        self.backdrop.size = self.size
        self.backdrop.visible = self.visible and self.dim_background

        page = self.current_page
        choice_count = 0 if page is None else len(page.choices)
        choice_area = 0.0
        if choice_count:
            choice_area = (
                choice_count * self.choice_button_height
                + max(0, choice_count - 1) * self.choice_gap
                + self.panel_padding
            )

        desired_height = max(
            160.0,
            self.panel_height + choice_area,
        )
        max_height = max(
            120.0,
            viewport_height - self.margin * 2.0,
        )
        panel_height = min(desired_height, max_height)
        panel_width = min(
            max(280.0, viewport_width - self.margin * 2.0),
            max(280.0, self.panel_width),
        )

        self.window.size = (panel_width, panel_height)
        self.window.position = (
            0.0,
            viewport_height / 2.0 - panel_height / 2.0 - self.margin,
        )
        self.window_shadow.size = (
            panel_width + 10.0,
            panel_height + 10.0,
        )
        self.window_shadow.position = (
            0.0,
            viewport_height / 2.0 - panel_height / 2.0 - self.margin + 6.0,
        )
        self.top_accent.size = (
            max(1.0, panel_width - 30.0),
            3.0,
        )
        self.top_accent.position = (
            0.0,
            -panel_height / 2.0 + 8.0,
        )

        portrait_edge = min(
            self.portrait_size,
            max(
                1.0,
                panel_height
                - self.panel_padding * 2.0
                - 30.0,
            ),
        )
        left_edge = -panel_width / 2.0 + self.panel_padding
        self.portrait_frame.size = (portrait_edge, portrait_edge)
        self.portrait_frame.position = (
            left_edge + portrait_edge / 2.0,
            -18.0,
        )
        self.portrait.size = (
            max(1.0, portrait_edge - 8.0),
            max(1.0, portrait_edge - 8.0),
        )

        portrait_x, portrait_y = self.portrait_frame.calculate_position()
        self.effects.set_positions(
            light=(portrait_x, portrait_y),
        )
        self.effects.visible = self._is_open and self.visible

        self.speaker_badge.size = (
            min(panel_width * 0.27, portrait_edge + 18.0),
            28.0,
        )
        self.speaker_badge.position = (
            left_edge + portrait_edge / 2.0,
            portrait_edge / 2.0 + 2.0,
        )
        self.speaker_label.position = (0.0, 0.0)

        self.text_divider.size = (
            2.0,
            max(1.0, panel_height - self.panel_padding * 2.0),
        )
        self.text_divider.position = (
            left_edge + portrait_edge + self.panel_padding / 2.0,
            0.0,
        )

        right_left = left_edge + portrait_edge + self.panel_padding
        right_width = max(
            1.0,
            panel_width - portrait_edge - self.panel_padding * 3.0,
        )
        content_top = -panel_height / 2.0 + self.panel_padding
        text_height = max(
            1.0,
            panel_height
            - self.panel_padding * 2.0
            - choice_area,
        )

        self.text_view.size = (right_width, text_height)
        self.text_view.position = (
            right_left + right_width / 2.0,
            content_top + text_height / 2.0,
        )

        self.choice_panel.size = (
            right_width,
            max(1.0, choice_area),
        )
        self.choice_panel.position = (
            right_left + right_width / 2.0,
            panel_height / 2.0
            - self.panel_padding
            - max(1.0, choice_area) / 2.0,
        )

        for index, button in enumerate(self._choice_buttons):
            button.size = (right_width, self.choice_button_height)
            button.anchor = (0.5, 0.5)
            button.pivot = (0.5, 0.5)
            button.position = (
                0.0,
                -max(1.0, choice_area) / 2.0
                + self.choice_button_height / 2.0
                + index * (self.choice_button_height + self.choice_gap),
            )

        hint_width = min(188.0, max(150.0, right_width * 0.34))
        hint_height = 34.0
        self.continue_hint_badge.size = (hint_width, hint_height)
        self.continue_hint_badge.position = (
            right_left + right_width - hint_width / 2.0 - 4.0,
            panel_height / 2.0 - self.panel_padding - hint_height / 2.0,
        )
        self.continue_hint_label.position = (0.0, 0.0)

        self._sync_choices()

    # ==============================================================
    # Input / rendering
    # ==============================================================

    def update_input(self, ui_input) -> None:
        if not self._is_open:
            return

        self._sync_layout()

        if ui_input.key_pressed(sdl3.SDL_SCANCODE_SPACE):
            if not self.text_finished:
                self._reveal_all()
            elif not (self.current_page and self.current_page.choices):
                self.advance()
            return

        super().update_input(ui_input)

    def render(self, renderer) -> None:
        if not self._is_open:
            return

        self._sync_layout()
        super().render(renderer)


__all__ = [
    "MAX_DIALOGUE_CHOICES",
    "DialogueChoice",
    "DialoguePage",
    "DialogueBox",
]
