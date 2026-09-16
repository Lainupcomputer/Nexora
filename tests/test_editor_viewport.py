from __future__ import annotations

import math

from nexora.editor.viewport import EditorViewportState


def test_world_screen_round_trip():
    state = EditorViewportState(
        x=25.0,
        y=-10.0,
        zoom=2.0,
    )

    screen = state.world_to_screen(
        40.0,
        15.0,
        300.0,
        200.0,
    )

    world = state.screen_to_world(
        *screen,
        300.0,
        200.0,
    )

    assert math.isclose(world[0], 40.0)
    assert math.isclose(world[1], 15.0)


def test_pan_uses_screen_delta_scaled_by_zoom():
    state = EditorViewportState(
        x=0.0,
        y=0.0,
        zoom=2.0,
    )

    state.pan_screen_delta(
        20.0,
        -10.0,
    )

    assert math.isclose(state.x, -10.0)
    assert math.isclose(state.y, 5.0)


def test_zoom_at_preserves_world_point_under_cursor():
    state = EditorViewportState(
        x=12.0,
        y=7.0,
        zoom=1.0,
    )

    cursor_x = 420.0
    cursor_y = 260.0
    center_x = 300.0
    center_y = 200.0

    before = state.screen_to_world(
        cursor_x,
        cursor_y,
        center_x,
        center_y,
    )

    state.zoom_at(
        cursor_x,
        cursor_y,
        center_x,
        center_y,
        1.5,
    )

    after = state.screen_to_world(
        cursor_x,
        cursor_y,
        center_x,
        center_y,
    )

    assert math.isclose(before[0], after[0])
    assert math.isclose(before[1], after[1])
    assert math.isclose(state.zoom, 1.5)


def test_zoom_clamps():
    state = EditorViewportState(
        zoom=1.0,
        min_zoom=0.25,
        max_zoom=3.0,
    )

    state.zoom_at(0.0, 0.0, 0.0, 0.0, 100.0)
    assert math.isclose(state.zoom, 3.0)

    state.zoom_at(0.0, 0.0, 0.0, 0.0, 0.0001)
    assert math.isclose(state.zoom, 0.25)
