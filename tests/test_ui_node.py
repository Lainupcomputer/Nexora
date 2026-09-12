
from nexora.scene import Scene, UINode
from nexora.nodes.panel import Panel
from nexora.nodes.button import Button
from nexora.nodes.ui_root import UIRoot
from nexora.ui import UIInput


def test_ui_node_creation() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    assert ui.name == "UI"
    assert ui.world is scene.world
    assert scene.world.is_alive(ui.entity)


def test_ui_node_defaults() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    assert ui.position == (0.0, 0.0)
    assert ui.size == (0.0, 0.0)

    assert ui.anchor == (0.5, 0.5)
    assert ui.pivot == (0.5, 0.5)

    assert ui.visible is True
    assert ui.enabled is True


def test_ui_node_hierarchy() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)
    panel = UINode("Panel", scene.world)

    ui.add_child(panel)

    assert panel.parent is ui
    assert panel in ui.children


def test_ui_node_configuration() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.position = (100.0, -50.0)
    ui.size = (300.0, 80.0)
    ui.anchor = (1.0, 0.0)
    ui.pivot = (1.0, 0.0)

    assert ui.position == (100.0, -50.0)
    assert ui.size == (300.0, 80.0)
    assert ui.anchor == (1.0, 0.0)
    assert ui.pivot == (1.0, 0.0)

def test_ui_node_center_position() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)
    ui.size = (200.0, 100.0)

    assert ui.calculate_position(1280, 720) == (0.0, 0.0)


def test_ui_node_top_left_anchor() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)
    ui.size = (200.0, 100.0)
    ui.anchor = (0.0, 0.0)
    ui.pivot = (0.0, 0.0)

    assert ui.calculate_position(1280, 720) == (-640.0, -360.0)


def test_ui_node_bottom_right_anchor() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)
    ui.size = (200.0, 100.0)
    ui.anchor = (1.0, 1.0)
    ui.pivot = (1.0, 1.0)

    assert ui.calculate_position(1280, 720) == (640.0, 360.0)

def test_ui_node_child_position() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)
    panel = UINode("Panel", scene.world)
    button = UINode("Button", scene.world)

    ui.position = (100.0, 50.0)
    panel.position = (20.0, 10.0)
    button.position = (5.0, 5.0)

    ui.add_child(panel)
    panel.add_child(button)

    assert ui.calculate_position(1280, 720) == (100.0, 50.0)
    assert panel.calculate_position(1280, 720) == (120.0, 60.0)
    assert button.calculate_position(1280, 720) == (125.0, 65.0)

def test_ui_node_non_ui_parent() -> None:
    scene = Scene("UITest")

    world = scene.create_node("World")
    ui = UINode("UI", scene.world)

    world.add_child(ui)

    ui.position = (100.0, 50.0)

    assert ui.calculate_position(1280, 720) == (100.0, 50.0)


def test_ui_node_rect() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.size = (200.0, 100.0)
    ui.set_viewport_size(1280, 720)

    assert ui.rect == (
        0.0,
        0.0,
        200.0,
        100.0,
    )


def test_ui_node_rect_with_anchor() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.size = (200.0, 100.0)
    ui.anchor = (1.0, 1.0)

    ui.set_viewport_size(1280, 720)

    assert ui.rect == (
        640.0,
        360.0,
        200.0,
        100.0,
    )

def test_ui_node_create_child() -> None:
    scene = Scene("UITest")

    scene.ui.set_viewport_size(1280, 720)

    panel = scene.ui.create_child("Panel")
    button = panel.create_child("Button")

    assert panel.parent is scene.ui
    assert button.parent is panel

    assert panel in scene.ui.children
    assert button in panel.children

    assert panel.world is scene.world
    assert button.world is scene.world

    assert panel._viewport_width == 1280.0
    assert panel._viewport_height == 720.0

    assert button._viewport_width == 1280.0
    assert button._viewport_height == 720.0

def test_ui_node_create_typed_child() -> None:
    scene = Scene("UITest")

    scene.ui.set_viewport_size(
        1280,
        720,
    )

    panel = scene.ui.create_child(
        "Panel",
        node_type=Panel,
    )

    assert isinstance(panel, Panel)
    assert panel.parent is scene.ui
    assert panel.world is scene.world

    assert panel._viewport_width == 1280.0
    assert panel._viewport_height == 720.0


class MockRenderer:
    def __init__(self) -> None:
        self.calls = []

    def rect(
        self,
        x,
        y,
        width,
        height,
        *,
        color,
        radius=0.0,
    ) -> None:
        self.calls.append(
            (
                x,
                y,
                width,
                height,
                color,
            )
        )


def test_ui_node_renders_children() -> None:
    scene = Scene("UITest")

    scene.ui.set_viewport_size(
        1280,
        720,
    )

    panel = scene.ui.create_child(
        "Panel",
        node_type=Panel,
    )

    panel.size = (
        400.0,
        200.0,
    )

    renderer = MockRenderer()

    scene.ui.render(renderer)

    assert renderer.calls == [
        (
            0.0,
            0.0,
            400.0,
            200.0,
            (
                32 / 255.0,
                34 / 255.0,
                37 / 255.0,
                1.0,
            ),
        )
    ]


def test_ui_node_contains_point_center() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.size = (
        200.0,
        100.0,
    )

    assert ui.contains_point(
        0.0,
        0.0,
    ) is True


def test_ui_node_contains_point_inside() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.size = (
        200.0,
        100.0,
    )

    assert ui.contains_point(
        50.0,
        20.0,
    ) is True


def test_ui_node_contains_point_outside() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.size = (
        200.0,
        100.0,
    )

    assert ui.contains_point(
        150.0,
        0.0,
    ) is False


def test_ui_node_contains_point_respects_pivot() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.size = (
        200.0,
        100.0,
    )

    ui.pivot = (
        0.0,
        0.0,
    )

    assert ui.contains_point(
        0.0,
        0.0,
    ) is True

    assert ui.contains_point(
        199.0,
        99.0,
    ) is True

    assert ui.contains_point(
        200.0,
        100.0,
    ) is True

    assert ui.contains_point(
        -1.0,
        0.0,
    ) is False


def test_ui_node_contains_point_with_position() -> None:
    scene = Scene("UITest")

    ui = UINode("UI", scene.world)

    ui.size = (
        200.0,
        100.0,
    )

    ui.position = (
        100.0,
        50.0,
    )

    assert ui.contains_point(
        100.0,
        50.0,
    ) is True

    assert ui.contains_point(
        199.0,
        99.0,
    ) is True

    assert ui.contains_point(
        -1.0,
        0.0,
    ) is False

def test_ui_node_dispatches_input_to_children() -> None:
    scene = Scene("UITest")

    ui = UIRoot(
        "UI",
        scene.world,
    )

    button = Button(
        "Button",
        scene.world,
    )

    button.size = (
        200.0,
        100.0,
    )

    ui.add_child(button)

    ui_input = UIInput()

    ui_input.set_mouse_position(
        50.0,
        20.0,
    )

    ui.update_input(
        ui_input,
    )

    assert button.hovered is True