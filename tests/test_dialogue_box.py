from __future__ import annotations

import pytest
import sdl3

from nexora.nodes import DialogueBox, DialogueChoice, DialoguePage
from nexora.scene import Scene
from nexora.ui import UIInput


def create_scene() -> Scene:
    scene = Scene("DialogueBoxTest")
    scene.ui.set_viewport_size(1280, 720)
    return scene


def press_space(scene: Scene) -> None:
    ui_input = UIInput()
    ui_input.update_keyboard(
        [],
        [sdl3.SDL_SCANCODE_SPACE],
        [],
    )
    scene.ui.update_input(ui_input)


def test_dialogue_box_reveals_and_advances_with_space() -> None:
    scene = create_scene()
    dialogue = scene.ui.create_child(
        "Dialogue",
        node_type=DialogueBox,
    )
    dialogue.characters_per_second = 10.0
    dialogue.set_pages(
        [
            DialoguePage("Jonas", "Hallo Welt."),
            DialoguePage("Jonas", "Die nächste Seite."),
        ]
    )
    dialogue.open()

    dialogue.update(0.2)
    assert dialogue.text_view.text == "Ha"
    assert dialogue.text_finished is False

    press_space(scene)
    assert dialogue.text_view.text == "Hallo Welt."
    assert dialogue.current_page_index == 0

    press_space(scene)
    assert dialogue.current_page_index == 1
    assert dialogue.is_open is True


def test_scene_update_advances_dialogue_typewriter() -> None:
    scene = create_scene()
    dialogue = scene.ui.create_child(
        "Dialogue",
        node_type=DialogueBox,
    )
    dialogue.characters_per_second = 20.0
    dialogue.set_pages([DialoguePage("Jonas", "Hallo Welt.")])
    dialogue.open()
    scene.enter()

    scene.update(0.25)

    assert dialogue.text_view.text == "Hallo"


def test_dialogue_box_choice_follows_target_page() -> None:
    scene = create_scene()
    dialogue = scene.ui.create_child(
        "Dialogue",
        node_type=DialogueBox,
    )
    selected: list[int] = []
    dialogue.choice_selected.connect(
        lambda _dialogue, _choice, index: selected.append(index)
    )
    dialogue.set_pages(
        [
            DialoguePage(
                "Jonas",
                "Möchtest du helfen?",
                choices=(
                    DialogueChoice("Ja", next_page=1),
                    DialogueChoice("Nein", next_page=2),
                ),
            ),
            DialoguePage("Jonas", "Dann los."),
            DialoguePage("Jonas", "Dann später."),
        ]
    )
    dialogue.open()
    dialogue.advance()

    assert dialogue._choice_buttons[0].visible is True
    assert dialogue._choice_buttons[0].enabled is True

    dialogue.choose(0)

    assert selected == [0]
    assert dialogue.current_page_index == 1


def test_dialogue_box_rejects_more_than_four_choices() -> None:
    choices = tuple(
        DialogueChoice(str(index))
        for index in range(5)
    )

    with pytest.raises(ValueError):
        DialoguePage("Jonas", "Zu viele Antworten.", choices=choices)


def test_dialogue_box_closes_after_last_page() -> None:
    scene = create_scene()
    dialogue = scene.ui.create_child(
        "Dialogue",
        node_type=DialogueBox,
    )
    dialogue.set_pages([DialoguePage("Jonas", "Ende.")])
    dialogue.open()

    dialogue.advance()
    assert dialogue.is_open is True
    dialogue.advance()

    assert dialogue.is_open is False
    assert scene.ui.active_modal is None
