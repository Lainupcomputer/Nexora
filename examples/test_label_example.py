from __future__ import annotations

import time
from pathlib import Path

import sdl3

from nexora.nodes import Label
from nexora.rendering.renderer import Renderer
from nexora.rendering.gpu.context import GPUContext
from nexora.rendering.text import TextSystem
from nexora.scene import Scene


ROOT = Path(__file__).resolve().parent.parent

FONT_PATH = (
    ROOT
    / "assets"
    / "fonts"
    / "Roboto-Regular.ttf"
)


def create_label(
    scene: Scene,
    name: str,
    text: str,
    *,
    anchor: tuple[float, float],
    pivot: tuple[float, float],
    position: tuple[float, float] = (0.0, 0.0),
    scale: float = 1.0,
    rotation: float = 0.0,
) -> Label:
    label = scene.ui.create_child(
        name,
        node_type=Label,
    )

    label.text = text
    label.anchor = anchor
    label.pivot = pivot
    label.position = position
    label.scale = scale
    label.rotation = rotation

    return label


def main() -> None:
    print("=" * 40)
    print(" Nexora Label / UI Test")
    print("=" * 40)
    print()

    if not FONT_PATH.is_file():
        raise FileNotFoundError(
            f"Font not found: {FONT_PATH}"
        )

    text_system = TextSystem()
    text_system.initialize()

    context = None
    font = None
    renderer = None

    try:
        print("Creating GPU context...")

        context = GPUContext(
            1280,
            720,
            title="Nexora - Label UI Test",
            debug=True,
            vsync=True,
        )

        print(f"GPU driver: {context.driver}")
        print(
            f"Swapchain format: "
            f"{context.swapchain_format}"
        )
        print()

        print("Loading font...")

        font = text_system.font(
            FONT_PATH,
            32,
        )

        print(f"Font: {font.path}")
        print(f"Size: {font.size}")
        print(f"Height: {font.height}")
        print(f"Ascent: {font.ascent}")
        print(f"Descent: {font.descent}")
        print(f"Line skip: {font.line_skip}")
        print()

        print("Creating Nexora renderer...")

        renderer = Renderer(
            context,
            font=font,
        )

        print()

        print("Creating scene...")

        scene = Scene("LabelExample")

        scene.ui.set_viewport_size(
            renderer.width,
            renderer.height,
        )

        # --------------------------------------------------
        # Centered label
        # --------------------------------------------------

        center_label = create_label(
            scene,
            "CenterLabel",
            "Nexora Engine",
            anchor=(0.5, 0.5),
            pivot=(0.5, 0.5),
            scale=1.5,
        )

        # --------------------------------------------------
        # Top-left label
        # --------------------------------------------------

        top_left_label = create_label(
            scene,
            "TopLeftLabel",
            "Top Left",
            anchor=(0.0, 0.0),
            pivot=(0.0, 0.0),
            position=(30.0, 30.0),
        )

        # --------------------------------------------------
        # Top-right label
        # --------------------------------------------------

        top_right_label = create_label(
            scene,
            "TopRightLabel",
            "Top Right",
            anchor=(1.0, 0.0),
            pivot=(1.0, 0.0),
            position=(-30.0, 30.0),
        )

        # --------------------------------------------------
        # Bottom-left label
        # --------------------------------------------------

        bottom_left_label = create_label(
            scene,
            "BottomLeftLabel",
            "Bottom Left",
            anchor=(0.0, 1.0),
            pivot=(0.0, 1.0),
            position=(30.0, -30.0),
        )

        # --------------------------------------------------
        # Bottom-right label
        # --------------------------------------------------

        bottom_right_label = create_label(
            scene,
            "BottomRightLabel",
            "Bottom Right",
            anchor=(1.0, 1.0),
            pivot=(1.0, 1.0),
            position=(-30.0, -30.0),
        )

        # --------------------------------------------------
        # Different scale
        # --------------------------------------------------

        create_label(
            scene,
            "SmallLabel",
            "Scale 0.75",
            anchor=(0.0, 0.5),
            pivot=(0.0, 0.5),
            position=(80.0, -60.0),
            scale=0.75,
        )

        create_label(
            scene,
            "LargeLabel",
            "Scale 2.0",
            anchor=(0.0, 0.5),
            pivot=(0.0, 0.5),
            position=(80.0, 20.0),
            scale=2.0,
        )

        # --------------------------------------------------
        # Rotation
        # --------------------------------------------------

        create_label(
            scene,
            "RotatedLabel",
            "Rotated",
            anchor=(0.75, 0.5),
            pivot=(0.5, 0.5),
            scale=1.2,
            rotation=0.15,
        )

        # --------------------------------------------------
        # UTF-8 / German characters
        # --------------------------------------------------

        create_label(
            scene,
            "UnicodeLabel",
            "ÄÖÜ äöü ß €",
            anchor=(0.5, 1.0),
            pivot=(0.5, 1.0),
            position=(0.0, -80.0),
        )

        # --------------------------------------------------
        # Multiline text
        # --------------------------------------------------

        create_label(
            scene,
            "MultilineLabel",
            "Line one\nLine two\nLine three",
            anchor=(1.0, 0.5),
            pivot=(1.0, 0.5),
            position=(-80.0, -40.0),
        )

        # --------------------------------------------------
        # Print calculated layout information
        # --------------------------------------------------

        print("UI layout:")
        print()

        for label in (
            center_label,
            top_left_label,
            top_right_label,
            bottom_left_label,
            bottom_right_label,
        ):
            position = label.calculate_position()

            width, height = renderer.text_measure(
                label.text,
                scale=label.scale,
            )

            baseline = renderer.text_baseline(
                scale=label.scale,
            )

            print(
                f"{label.name}:"
            )
            print(
                f"  position: "
                f"({position[0]:.2f}, "
                f"{position[1]:.2f})"
            )
            print(
                f"  size: "
                f"({width:.2f}, "
                f"{height:.2f})"
            )
            print(
                f"  baseline: "
                f"{baseline:.2f}"
            )
            print(
                f"  anchor: "
                f"{label.anchor}"
            )
            print(
                f"  pivot: "
                f"{label.pivot}"
            )
            print()

        print("Rendering test scene...")
        print("Close the window or press ESC to finish.")
        print()

        running = True

        while running:
            for event in context.poll_events():
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif event.type == sdl3.SDL_EVENT_KEY_DOWN:
                    if event.key.key == sdl3.SDLK_ESCAPE:
                        running = False

            if not running:
                break

            if not renderer.begin_frame():
                time.sleep(0.001)
                continue

            try:
                scene.ui.render(
                    renderer,
                )

                if not renderer.end_frame():
                    break

            except Exception:
                context.cancel_frame()
                raise

            time.sleep(0.001)

    finally:
        print()
        print("Cleaning up...")

        scene = locals().get("scene")

        if scene is not None:
            scene.destroy()

        if renderer is not None:
            renderer.destroy()

        if font is not None:
            font.close()

        if context is not None:
            context.destroy()

        text_system.shutdown()

        print("Done.")


if __name__ == "__main__":
    main()