from nexora.ecs.world import World
from nexora.nodes.panel import Panel


def test_panel_creation() -> None:
    world = World()

    panel = Panel(
        "Panel",
        world,
    )

    assert panel.name == "Panel"
    assert panel.world is world

    assert panel.visible is True
    assert panel.enabled is True

    assert panel.position == (0.0, 0.0)
    assert panel.size == (0.0, 0.0)

    assert panel.anchor == (0.5, 0.5)
    assert panel.pivot == (0.5, 0.5)

    assert panel.background == (
        32,
        34,
        37,
        255,
    )


def test_panel_can_have_children() -> None:
    world = World()

    panel = Panel(
        "Panel",
        world,
    )

    child = panel.create_child("Child")

    assert child.parent is panel
    assert child in panel.children
    assert child.world is world


def test_panel_position() -> None:
    world = World()

    panel = Panel(
        "Panel",
        world,
    )

    panel.size = (
        400.0,
        200.0,
    )

    panel.anchor = (
        0.5,
        0.5,
    )

    panel.position = (
        100.0,
        50.0,
    )

    panel.set_viewport_size(
        1280,
        720,
    )

    assert panel.rect == (
        100.0,
        50.0,
        400.0,
        200.0,
    )

    assert panel.border_color == (
        0,
        0,
        0,
        0,
    )

    assert panel.border_width == 0.0
    assert panel.border_radius == 0.0

def test_panel_style() -> None:
    world = World()

    panel = Panel(
        "Panel",
        world,
    )

    panel.background = (
        20,
        22,
        26,
        255,
    )

    panel.border_color = (
        120,
        120,
        120,
        255,
    )

    panel.border_width = 2.0
    panel.border_radius = 8.0


    assert panel.background == (
        20,
        22,
        26,
        255,
    )

    assert panel.border_color == (
        120,
        120,
        120,
        255,
    )

    assert panel.border_width == 2.0
    assert panel.border_radius == 8.0

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

def test_panel_render() -> None:
    world = World()

    panel = Panel(
        "Panel",
        world,
    )

    panel.size = (
        400.0,
        200.0,
    )

    panel.anchor = (
        0.5,
        0.5,
    )

    panel.set_viewport_size(
        1280,
        720,
    )

    renderer = MockRenderer()

    panel.render(renderer)

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
