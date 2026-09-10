from __future__ import annotations

import pytest


pytestmark = pytest.mark.gpu


def test_gpu_context():
    from nexora.rendering.gpu.context import GPUContext

    context = GPUContext(
        640,
        480,
        "Nexora Test",
        debug=True,
        frames_in_flight=2,
        vsync=True,
    )

    try:
        assert context.initialized
        assert context.device is not None
        assert context.window is not None
        assert context.driver
    finally:
        context.destroy()


def test_gpu_frame():
    from nexora.rendering.gpu.context import GPUContext

    context = GPUContext(
        640,
        480,
        "Nexora GPU Test",
        debug=True,
        frames_in_flight=2,
        vsync=True,
    )

    try:
        if not context.begin_frame():
            pytest.skip("GPU swapchain frame could not be acquired")

        try:
            render_pass = context.begin_render_pass(
                (0.05, 0.05, 0.08, 1.0)
            )

            try:
                assert render_pass is not None
            finally:
                context.end_render_pass(render_pass)

        finally:
            context.end_frame()

    finally:
        context.destroy()