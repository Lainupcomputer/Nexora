from __future__ import annotations

import pytest

from nexora.ecs.world import World
from nexora.nodes import (
    HBoxContainer,
    Panel,
    UINode,
    VBoxContainer,
)


# ==============================================================
# Helpers
# ==============================================================


def create_node(
    node_type=UINode,
    name: str = "Node",
):
    """
    Create a UI node with a real Nexora ECS World.

    Node.__init__() creates an ECS entity, therefore the tests must
    use a real World instead of a dummy object.
    """

    world = World()

    return node_type(
        name,
        world,
    )


# ==============================================================
# UINode sizing
# ==============================================================


def test_fixed_size_mode_keeps_explicit_size():
    node = create_node()

    node.size = (
        200.0,
        100.0,
    )

    node.width_mode = "fixed"
    node.height_mode = "fixed"

    size = node.measure(
        1000.0,
        800.0,
    )

    assert size == (
        200.0,
        100.0,
    )


def test_fill_size_mode_uses_available_space():
    node = create_node()

    node.width_mode = "fill"
    node.height_mode = "fill"

    size = node.measure(
        800.0,
        600.0,
    )

    assert size == (
        800.0,
        600.0,
    )


def test_percent_size_mode_uses_percentage():
    node = create_node()

    node.width_mode = "percent"
    node.height_mode = "percent"

    node.width_percent = 0.25
    node.height_percent = 0.5

    size = node.measure(
        800.0,
        600.0,
    )

    assert size == (
        200.0,
        300.0,
    )


def test_min_size_is_respected():
    node = create_node()

    node.size = (
        10.0,
        20.0,
    )

    node.min_size = (
        100.0,
        80.0,
    )

    size = node.measure(
        500.0,
        500.0,
    )

    assert size == (
        100.0,
        80.0,
    )


def test_arrange_respects_min_size():
    node = create_node()

    node.min_size = (
        100.0,
        80.0,
    )

    node.arrange(
        20.0,
        30.0,
    )

    assert node.size == (
        100.0,
        80.0,
    )


def test_invalid_width_mode_raises():
    node = create_node()

    node.width_mode = "banana"

    with pytest.raises(
        ValueError
    ):
        node.measure(
            500.0,
            500.0,
        )


# ==============================================================
# VBox positioning
# ==============================================================


def test_vbox_positions_children_vertically():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        400.0,
        400.0,
    )

    box.spacing = 10.0
    box.alignment = "start"

    a = box.create_child(
        "A",
        node_type=Panel,
    )

    b = box.create_child(
        "B",
        node_type=Panel,
    )

    a.size = (
        100.0,
        50.0,
    )

    b.size = (
        100.0,
        70.0,
    )

    box.measure(
        400.0,
        400.0,
    )

    box.arrange(
        400.0,
        400.0,
    )

    assert a.position == pytest.approx(
        (
            50.0,
            25.0,
        )
    )

    assert b.position == pytest.approx(
        (
            50.0,
            95.0,
        )
    )


# ==============================================================
# VBox grow
# ==============================================================


def test_vbox_grow_uses_remaining_height():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        400.0,
        400.0,
    )

    box.spacing = 10.0

    header = box.create_child(
        "Header",
        node_type=Panel,
    )

    content = box.create_child(
        "Content",
        node_type=Panel,
    )

    footer = box.create_child(
        "Footer",
        node_type=Panel,
    )

    header.size = (
        100.0,
        50.0,
    )

    footer.size = (
        100.0,
        50.0,
    )

    content.min_size = (
        0.0,
        100.0,
    )

    content.layout_grow = 1.0

    box.measure(
        400.0,
        400.0,
    )

    box.arrange(
        400.0,
        400.0,
    )

    # 400 total
    #
    # fixed:
    #   header = 50
    #   footer = 50
    #
    # spacing:
    #   2 * 10 = 20
    #
    # remaining:
    #   400 - 50 - 50 - 20 = 280

    assert content.size[1] == pytest.approx(
        280.0
    )


def test_vbox_grow_ratio():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        300.0,
        500.0,
    )

    box.spacing = 0.0

    a = box.create_child(
        "A",
        node_type=Panel,
    )

    b = box.create_child(
        "B",
        node_type=Panel,
    )

    a.min_size = (
        0.0,
        50.0,
    )

    b.min_size = (
        0.0,
        50.0,
    )

    a.layout_grow = 1.0
    b.layout_grow = 3.0

    box.measure(
        300.0,
        500.0,
    )

    box.arrange(
        300.0,
        500.0,
    )

    # Base:
    #   A = 50
    #   B = 50
    #
    # Free:
    #   500 - 100 = 400
    #
    # Grow ratio 1:3:
    #   A receives 100
    #   B receives 300
    #
    # Final:
    #   A = 150
    #   B = 350

    assert a.size[1] == pytest.approx(
        150.0
    )

    assert b.size[1] == pytest.approx(
        350.0
    )


# ==============================================================
# HBox positioning
# ==============================================================


def test_hbox_positions_children_horizontally():
    box = create_node(
        HBoxContainer,
        "HBox",
    )

    box.size = (
        400.0,
        200.0,
    )

    box.spacing = 10.0
    box.alignment = "start"

    a = box.create_child(
        "A",
        node_type=Panel,
    )

    b = box.create_child(
        "B",
        node_type=Panel,
    )

    a.size = (
        50.0,
        40.0,
    )

    b.size = (
        70.0,
        40.0,
    )

    box.measure(
        400.0,
        200.0,
    )

    box.arrange(
        400.0,
        200.0,
    )

    assert a.position == pytest.approx(
        (
            25.0,
            20.0,
        )
    )

    assert b.position == pytest.approx(
        (
            95.0,
            20.0,
        )
    )


# ==============================================================
# HBox grow
# ==============================================================


def test_hbox_grow_ratio_1_2_1():
    box = create_node(
        HBoxContainer,
        "HBox",
    )

    box.size = (
        500.0,
        200.0,
    )

    box.spacing = 0.0

    left = box.create_child(
        "Left",
        node_type=Panel,
    )

    center = box.create_child(
        "Center",
        node_type=Panel,
    )

    right = box.create_child(
        "Right",
        node_type=Panel,
    )

    left.min_size = (
        50.0,
        0.0,
    )

    center.min_size = (
        50.0,
        0.0,
    )

    right.min_size = (
        50.0,
        0.0,
    )

    left.layout_grow = 1.0
    center.layout_grow = 2.0
    right.layout_grow = 1.0

    box.measure(
        500.0,
        200.0,
    )

    box.arrange(
        500.0,
        200.0,
    )

    # Base:
    #
    #   50 + 50 + 50 = 150
    #
    # Free:
    #
    #   500 - 150 = 350
    #
    # Grow ratio:
    #
    #   1 : 2 : 1
    #
    # Extra:
    #
    #   Left   = 87.5
    #   Center = 175
    #   Right  = 87.5
    #
    # Final:
    #
    #   Left   = 137.5
    #   Center = 225
    #   Right  = 137.5

    assert left.size[0] == pytest.approx(
        137.5
    )

    assert center.size[0] == pytest.approx(
        225.0
    )

    assert right.size[0] == pytest.approx(
        137.5
    )


# ==============================================================
# Alignment
# ==============================================================


def test_vbox_center_alignment():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        400.0,
        300.0,
    )

    box.alignment = "center"

    child = box.create_child(
        "Child",
        node_type=Panel,
    )

    child.size = (
        100.0,
        50.0,
    )

    box.measure(
        400.0,
        300.0,
    )

    box.arrange(
        400.0,
        300.0,
    )

    assert child.position[0] == pytest.approx(
        200.0
    )


def test_vbox_end_alignment():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        400.0,
        300.0,
    )

    box.padding_right = 20.0
    box.alignment = "end"

    child = box.create_child(
        "Child",
        node_type=Panel,
    )

    child.size = (
        100.0,
        50.0,
    )

    box.measure(
        400.0,
        300.0,
    )

    box.arrange(
        400.0,
        300.0,
    )

    # Right edge:
    #
    #   400 - 20 = 380
    #
    # Center:
    #
    #   380 - 50 = 330

    assert child.position[0] == pytest.approx(
        330.0
    )


# ==============================================================
# Stretch
# ==============================================================


def test_vbox_stretch_sets_child_width():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        400.0,
        300.0,
    )

    box.padding_left = 20.0
    box.padding_right = 30.0

    box.alignment = "stretch"

    child = box.create_child(
        "Child",
        node_type=Panel,
    )

    child.size = (
        100.0,
        50.0,
    )

    box.measure(
        400.0,
        300.0,
    )

    box.arrange(
        400.0,
        300.0,
    )

    # 400 - 20 - 30 = 350

    assert child.size[0] == pytest.approx(
        350.0
    )


def test_layout_stretch_false_preserves_width():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        400.0,
        300.0,
    )

    box.alignment = "stretch"

    child = box.create_child(
        "Child",
        node_type=Panel,
    )

    child.size = (
        120.0,
        50.0,
    )

    child.layout_stretch = False

    box.measure(
        400.0,
        300.0,
    )

    box.arrange(
        400.0,
        300.0,
    )

    assert child.size[0] == pytest.approx(
        120.0
    )


# ==============================================================
# Padding
# ==============================================================


def test_vbox_padding_affects_position():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.size = (
        400.0,
        300.0,
    )

    box.padding_left = 20.0
    box.padding_top = 30.0

    box.alignment = "start"

    child = box.create_child(
        "Child",
        node_type=Panel,
    )

    child.size = (
        100.0,
        50.0,
    )

    box.measure(
        400.0,
        300.0,
    )

    box.arrange(
        400.0,
        300.0,
    )

    assert child.position == pytest.approx(
        (
            70.0,
            55.0,
        )
    )


# ==============================================================
# fit_content
# ==============================================================


def test_vbox_fit_content_uses_children():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.fit_content = True

    box.spacing = 10.0

    box.padding_left = 5.0
    box.padding_right = 5.0

    box.padding_top = 10.0
    box.padding_bottom = 10.0

    a = box.create_child(
        "A",
        node_type=Panel,
    )

    b = box.create_child(
        "B",
        node_type=Panel,
    )

    a.size = (
        100.0,
        40.0,
    )

    b.size = (
        150.0,
        60.0,
    )

    size = box.measure(
        1000.0,
        1000.0,
    )

    # Width:
    #
    #   max(100, 150)
    #   + 5 left
    #   + 5 right
    #
    # = 160
    #
    # Height:
    #
    #   40
    #   + 60
    #   + 10 spacing
    #   + 10 top
    #   + 10 bottom
    #
    # = 130

    assert size[0] == pytest.approx(
        160.0
    )

    assert size[1] == pytest.approx(
        130.0
    )


def test_hbox_fit_content_uses_children():
    box = create_node(
        HBoxContainer,
        "HBox",
    )

    box.fit_content = True

    box.spacing = 10.0

    box.padding_left = 10.0
    box.padding_right = 10.0

    box.padding_top = 5.0
    box.padding_bottom = 5.0

    a = box.create_child(
        "A",
        node_type=Panel,
    )

    b = box.create_child(
        "B",
        node_type=Panel,
    )

    a.size = (
        100.0,
        40.0,
    )

    b.size = (
        150.0,
        60.0,
    )

    size = box.measure(
        1000.0,
        1000.0,
    )

    # Width:
    #
    # 100 + 150 + 10 spacing + 20 padding
    # = 280
    #
    # Height:
    #
    # max(40, 60) + 10 padding
    # = 70

    assert size[0] == pytest.approx(
        280.0
    )

    assert size[1] == pytest.approx(
        70.0
    )


# ==============================================================
# Nested measure
# ==============================================================


def test_nested_fit_content_stabilizes_in_one_measure():
    outer = create_node(
        VBoxContainer,
        "Outer",
    )

    outer.fit_content = True

    inner = outer.create_child(
        "Inner",
        node_type=VBoxContainer,
    )

    inner.fit_content = True
    inner.spacing = 10.0

    a = inner.create_child(
        "A",
        node_type=Panel,
    )

    b = inner.create_child(
        "B",
        node_type=Panel,
    )

    a.size = (
        100.0,
        50.0,
    )

    b.size = (
        100.0,
        70.0,
    )

    first = outer.measure(
        1000.0,
        1000.0,
    )

    second = outer.measure(
        1000.0,
        1000.0,
    )

    # The important part:
    #
    # A second layout pass must not change the result.

    assert first == pytest.approx(
        second
    )

    assert first[0] == pytest.approx(
        100.0
    )

    assert first[1] == pytest.approx(
        130.0
    )


# ==============================================================
# Percent sizing
# ==============================================================


def test_percent_child_inside_hbox():
    box = create_node(
        HBoxContainer,
        "HBox",
    )

    box.size = (
        1000.0,
        300.0,
    )

    box.padding_left = 20.0
    box.padding_right = 20.0

    child = box.create_child(
        "PercentChild",
        node_type=Panel,
    )

    child.width_mode = "percent"
    child.width_percent = 0.25

    child.size = (
        0.0,
        50.0,
    )

    box.measure(
        1000.0,
        300.0,
    )

    box.arrange(
        1000.0,
        300.0,
    )

    # Inner width:
    #
    #   1000 - 20 - 20 = 960
    #
    # 25%:
    #
    #   960 * 0.25 = 240

    assert child.size[0] == pytest.approx(
        240.0
    )


def test_percent_child_respects_minimum_width():
    box = create_node(
        HBoxContainer,
        "HBox",
    )

    box.size = (
        400.0,
        200.0,
    )

    child = box.create_child(
        "PercentChild",
        node_type=Panel,
    )

    child.width_mode = "percent"
    child.width_percent = 0.10

    child.min_size = (
        100.0,
        0.0,
    )

    child.size = (
        0.0,
        50.0,
    )

    box.measure(
        400.0,
        200.0,
    )

    box.arrange(
        400.0,
        200.0,
    )

    # 10% would only be 40px,
    # therefore min_size must win.

    assert child.size[0] == pytest.approx(
        100.0
    )


# ==============================================================
# Fill sizing
# ==============================================================


def test_fill_child_measure_uses_available_space():
    node = create_node(
        Panel,
        "FillNode",
    )

    node.width_mode = "fill"
    node.height_mode = "fill"

    size = node.measure(
        640.0,
        480.0,
    )

    assert size == pytest.approx(
        (
            640.0,
            480.0,
        )
    )


# ==============================================================
# Hidden children
# ==============================================================


def test_hidden_child_is_ignored_by_box_layout():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.fit_content = True
    box.spacing = 10.0

    visible = box.create_child(
        "Visible",
        node_type=Panel,
    )

    hidden = box.create_child(
        "Hidden",
        node_type=Panel,
    )

    visible.size = (
        100.0,
        50.0,
    )

    hidden.size = (
        500.0,
        500.0,
    )

    hidden.visible = False

    size = box.measure(
        1000.0,
        1000.0,
    )

    assert size == pytest.approx(
        (
            100.0,
            50.0,
        )
    )


# ==============================================================
# Stability
# ==============================================================


def test_measure_is_stable():
    box = create_node(
        VBoxContainer,
        "VBox",
    )

    box.fit_content = True

    child = box.create_child(
        "Child",
        node_type=Panel,
    )

    child.size = (
        120.0,
        80.0,
    )

    first = box.measure(
        800.0,
        600.0,
    )

    second = box.measure(
        800.0,
        600.0,
    )

    third = box.measure(
        800.0,
        600.0,
    )

    assert first == pytest.approx(
        second
    )

    assert second == pytest.approx(
        third
    )