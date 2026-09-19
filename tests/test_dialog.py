from __future__ import annotations

from pathlib import Path

import sdl3

from nexora.nodes import Button, ConfirmDialog, Dialog, FileDialog
from nexora.scene import Scene
from nexora.ui import UIInput


def create_scene() -> Scene:
    scene = Scene("DialogTest")
    scene.ui.set_viewport_size(1280, 720)
    return scene


def test_dialog_starts_closed() -> None:
    scene = create_scene()
    dialog = scene.ui.create_child("Dialog", node_type=Dialog)

    assert dialog.is_open is False
    assert dialog.visible is False
    assert dialog.enabled is False


def test_open_dialog_activates_modal_scope_and_focus() -> None:
    scene = create_scene()
    behind = scene.ui.create_child("Behind", node_type=Button)
    behind.size = (200.0, 50.0)
    behind.focus()

    dialog = scene.ui.create_child("Dialog", node_type=Dialog)
    dialog.open()

    assert scene.ui.active_modal is dialog
    assert dialog.is_open is True
    assert scene.ui.focused_node is dialog.confirm_button


def test_close_dialog_restores_previous_focus() -> None:
    scene = create_scene()
    behind = scene.ui.create_child("Behind", node_type=Button)
    behind.size = (200.0, 50.0)
    behind.focus()

    dialog = scene.ui.create_child("Dialog", node_type=Dialog)
    dialog.open()
    dialog.close()

    assert scene.ui.active_modal is None
    assert scene.ui.focused_node is behind


def test_escape_cancels_dialog() -> None:
    scene = create_scene()
    dialog = scene.ui.create_child("Dialog", node_type=Dialog)
    cancelled: list[bool] = []
    dialog.cancelled.connect(lambda *_: cancelled.append(True))
    dialog.open()

    ui_input = UIInput()
    ui_input.update_keyboard([], [sdl3.SDL_SCANCODE_ESCAPE], [])
    scene.ui.update_input(ui_input)

    assert cancelled == [True]
    assert dialog.is_open is False


def test_enter_confirms_dialog() -> None:
    scene = create_scene()
    dialog = scene.ui.create_child("Dialog", node_type=Dialog)
    confirmed: list[bool] = []
    dialog.confirmed.connect(lambda *_: confirmed.append(True))
    dialog.open()

    ui_input = UIInput()
    ui_input.update_keyboard([], [sdl3.SDL_SCANCODE_RETURN], [])
    scene.ui.update_input(ui_input)

    assert confirmed == [True]
    assert dialog.is_open is False


def test_modal_dialog_blocks_controls_behind_it() -> None:
    scene = create_scene()
    clicked: list[str] = []

    behind = scene.ui.create_child("Behind", node_type=Button)
    behind.size = (300.0, 100.0)
    behind.position = (0.0, 0.0)
    behind.on_click = lambda: clicked.append("behind")

    dialog = scene.ui.create_child("Dialog", node_type=Dialog)
    dialog.open()

    ui_input = UIInput()
    ui_input.update_mouse((0.0, 0.0), True, True, False)
    scene.ui.update_input(ui_input)
    ui_input.update_mouse((0.0, 0.0), False, False, True)
    scene.ui.update_input(ui_input)

    assert clicked == []


def test_confirm_dialog_message() -> None:
    scene = create_scene()
    dialog = scene.ui.create_child("Confirm", node_type=ConfirmDialog)
    dialog.message = "Delete this node?"
    dialog.open()
    dialog._sync_layout()

    assert dialog.message_label.text == "Delete this node?"


def test_file_dialog_filters_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.nxscene").write_text("scene")
    (tmp_path / "b.txt").write_text("text")
    (tmp_path / "folder").mkdir()

    scene = create_scene()
    dialog = scene.ui.create_child("Files", node_type=FileDialog)
    dialog.configure(
        mode="open",
        root_path=tmp_path,
        extensions=(".nxscene",),
    )

    assert "a.nxscene" in dialog.file_list.items
    assert "b.txt" not in dialog.file_list.items
    assert "[folder]" in dialog.file_list.items


def test_file_dialog_hides_technical_directories(tmp_path: Path) -> None:
    for name in (".git", ".github", ".pytest_cache", ".venv", "Bruch", "assets"):
        (tmp_path / name).mkdir()

    scene = create_scene()
    dialog = scene.ui.create_child("Files", node_type=FileDialog)
    dialog.configure(mode="open", root_path=tmp_path)

    assert dialog.file_list.items == ["[assets]"]


def test_file_dialog_save_adds_extension(tmp_path: Path) -> None:
    scene = create_scene()
    dialog = scene.ui.create_child("Files", node_type=FileDialog)
    dialog.configure(
        mode="save",
        root_path=tmp_path,
        extensions=("nxscene",),
    )
    dialog.open(focus=dialog.filename_input)
    dialog.filename_input.set_text("level_01", emit=False)

    selected: list[Path] = []
    dialog.file_selected.connect(lambda _dialog, path: selected.append(path))
    dialog.confirm()

    assert selected == [tmp_path / "level_01.nxscene"]
    assert dialog.is_open is False


def test_file_dialog_can_select_a_directory(tmp_path: Path) -> None:
    project = tmp_path / "MyGame"
    project.mkdir()

    scene = create_scene()
    dialog = scene.ui.create_child("Projects", node_type=FileDialog)
    dialog.configure(
        mode="open",
        root_path=tmp_path,
        title="Choose Project Folder",
    )
    dialog.allow_directories = True
    dialog.open()

    selected: list[Path] = []
    dialog.file_selected.connect(lambda _dialog, path: selected.append(path))
    index = dialog.file_list.items.index("[MyGame]")
    dialog._on_list_change(index, "[MyGame]")
    dialog.confirm()

    assert selected == [project]
    assert dialog.is_open is False
