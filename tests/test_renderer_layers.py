from nexora.rendering.gpu.renderer import GPURenderer


def test_layer_scope_offsets_queued_commands_and_restores_state() -> None:
    renderer = GPURenderer.__new__(GPURenderer)
    renderer._layer_offset = 0
    renderer._render_commands = []
    renderer._render_command_phases = []
    renderer._submission_index = 0
    renderer._render_phase = "overlay"

    renderer._queue_render_command("rect", 0, 1, 10)
    with renderer.layer_scope(200_000):
        renderer._queue_render_command("rect", 1, 1, 20)
        with renderer.layer_scope(5):
            renderer._queue_render_command("rect", 2, 1, 30)

    renderer._queue_render_command("rect", 3, 1, 40)

    assert [command[0] for command in renderer._render_commands] == [
        10,
        200_020,
        200_035,
        40,
    ]
    assert renderer.layer_offset == 0
