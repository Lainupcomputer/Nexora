import time

from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.gpu.shape_batch import GPUShapeBatch


def main():
    print("=" * 40)
    print(" Nexora GPU Shape Renderer Test")
    print("=" * 40)
    print()

    print("Creating GPU context...")

    context = GPUContext(
        1280,
        720,
        title="Nexora - GPU Shape Test",
        debug=True,
        vsync=True,
    )

    print("GPU context ready.")
    print(f"GPU driver: {context.driver}")
    print(f"Swapchain format: {context.swapchain_format}")
    print()

    renderer = GPUShapeBatch(
        context,
        max_shapes=100,
        vertex_shader_path="nexora/rendering/shaders/bin/shape.vert.spv",
        fragment_shader_path="nexora/rendering/shaders/bin/shape.frag.spv",
    )

    print("Shape renderer ready.")
    print()

    running = True

    while running:

        # ---------------------------------------------------------
        # Events
        # ---------------------------------------------------------

        events = context.poll_events()

        for event in events:
            event_type = getattr(event, "type", None)

            # SDL_EVENT_QUIT
            if event_type == 0x100:
                running = False

        # ---------------------------------------------------------
        # Clear renderer
        # ---------------------------------------------------------

        renderer.clear()

        # =========================================================
        # Basic shapes
        # =========================================================

        # Red rectangle
        renderer.rect(
            -500,
            -220,
            180,
            100,
            color=(1.0, 0.1, 0.1, 1.0),
        )

        # Green ellipse
        renderer.ellipse(
            -250,
            -220,
            180,
            100,
            color=(0.1, 1.0, 0.2, 1.0),
        )

        # Blue circle
        renderer.circle(
            20,
            -220,
            100,
            color=(0.1, 0.4, 1.0, 1.0),
        )

        # =========================================================
        # Triangle
        # =========================================================

        renderer.triangle(
            -300,
            100,
            -50,
            -80,
            200,
            100,
            color=(1.0, 0.8, 0.1, 1.0),
        )

        # =========================================================
        # Polygon
        # =========================================================

        renderer.polygon(
            [
                (250, 80),
                (400, 80),
                (470, 180),
                (325, 250),
                (180, 180),
            ],
            color=(0.7, 0.2, 1.0, 1.0),
        )

        # =========================================================
        # Rotation + Origin tests
        # =========================================================

        # ---------------------------------------------------------
        # Center origin
        # Rotation happens around the center
        # ---------------------------------------------------------

        renderer.rect(
            -500,
            100,
            160,
            80,
            rotation=25,
            origin=(0.5, 0.5),
            color=(1.0, 0.3, 0.3, 1.0),
        )

        # ---------------------------------------------------------
        # Top-left origin
        # Rotation happens around the top-left corner
        # ---------------------------------------------------------

        renderer.rect(
            -250,
            100,
            160,
            80,
            rotation=25,
            origin=(0.0, 0.0),
            color=(0.3, 1.0, 0.3, 1.0),
        )

        # ---------------------------------------------------------
        # Bottom-right origin
        # Rotation happens around the bottom-right corner
        # ---------------------------------------------------------

        renderer.rect(
            0,
            100,
            160,
            80,
            rotation=25,
            origin=(1.0, 1.0),
            color=(0.3, 0.5, 1.0, 1.0),
        )

        # =========================================================
        # Rotated ellipse
        # =========================================================

        renderer.ellipse(
            300,
            -100,
            180,
            90,
            rotation=35,
            origin=(0.5, 0.5),
            color=(1.0, 0.4, 0.1, 1.0),
        )

        # =========================================================
        # Rotated circle
        # =========================================================

        renderer.circle(
            450,
            -250,
            100,
            rotation=45,
            origin=(0.5, 0.5),
            color=(0.2, 1.0, 0.8, 1.0),
        )

        # =========================================================
        # Begin frame
        # =========================================================

        if not context.begin_frame():
            continue

        # Upload renderer data
        renderer.render_into(
            context.command_buffer
        )

        # ---------------------------------------------------------
        # Render pass
        # ---------------------------------------------------------

        render_pass = context.begin_render_pass(
            clear_color=(0.04, 0.04, 0.06, 1.0)
        )

        # Draw everything
        renderer.draw_into(
            render_pass
        )

        # End render pass
        context.end_render_pass(
            render_pass
        )

        # Submit frame
        context.end_frame()

        time.sleep(0.001)

    # =============================================================
    # Cleanup
    # =============================================================

    renderer.destroy()
    context.destroy()

    print()
    print("Shape renderer test finished.")


if __name__ == "__main__":
    main()