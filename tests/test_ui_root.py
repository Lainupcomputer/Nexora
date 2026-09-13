
from nexora.scene import Scene, UINode, UIRoot


def test_ui_root_viewport_propagation() -> None:
    scene = Scene("UITest")

    root = UIRoot("UI", scene.world)
    panel = UINode("Panel", scene.world)
    button = UINode("Button", scene.world)

    root.add_child(panel)
    panel.add_child(button)

    root.set_viewport_size(1280, 720)

    assert root.calculate_position() == (0.0, 0.0)
    assert panel.calculate_position() == (0.0, 0.0)
    assert button.calculate_position() == (0.0, 0.0)


def test_ui_root_viewport_resize() -> None:
    scene = Scene("UITest")

    root = UIRoot("UI", scene.world)
    panel = UINode("Panel", scene.world)

    root.add_child(panel)

    panel.anchor = (1.0, 1.0)

    root.set_viewport_size(1280, 720)

    assert panel.calculate_position() == (640.0, 360.0)

    root.set_viewport_size(1920, 1080)

    assert panel.calculate_position() == (960.0, 540.0)