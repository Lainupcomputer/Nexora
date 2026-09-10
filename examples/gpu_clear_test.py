from __future__ import annotations

import sdl3

from nexora.debug.logger import Logger
from nexora.threading.context import ThreadContext
from nexora.rendering.gpu import GPUContext


def main() -> None:
    ThreadContext.initialize()

    logger = Logger()

    gpu = None

    try:
        logger.info(
            "Creating Nexora GPU context..."
        )

        gpu = GPUContext(
            width=1280,
            height=720,
            title="Nexora GPU Clear Test",
            resizable=True,
            debug=True,
            allowed_frames_in_flight=2,
        )

        logger.info(
            f"GPU driver: {gpu.driver}"
        )

        logger.info(
            f"Swapchain format: "
            f"{gpu.swapchain_format}"
        )

        logger.info(
            "GPU initialization successful."
        )

        running = True

        while running:

            event = sdl3.SDL_Event()

            while sdl3.SDL_PollEvent(event):

                if event.type == (
                    sdl3.SDL_EVENT_QUIT
                ):
                    running = False

                elif event.type == (
                    sdl3.SDL_EVENT_KEY_DOWN
                ):
                    if (
                        event.key.key
                        == sdl3.SDLK_ESCAPE
                    ):
                        running = False

                elif event.type == (
                    sdl3.SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED
                ):
                    logger.info(
                        "Window size changed."
                    )

            # ------------------------------------------------------
            # GPU FRAME
            # ------------------------------------------------------

            command_buffer = gpu.begin_frame()

            # Window can be minimized.
            if command_buffer is None:
                sdl3.SDL_Delay(10)
                continue

            render_pass = gpu.begin_render_pass(
                clear_color=(
                    0.03,
                    0.05,
                    0.08,
                    1.0,
                )
            )

            if render_pass is not None:
                gpu.end_render_pass(
                    render_pass
                )

            gpu.end_frame()

        logger.info(
            "Waiting for GPU..."
        )

        gpu.wait_idle()

        logger.info(
            "GPU clear test finished."
        )

    except Exception:
        if gpu is not None:
            try:
                gpu.destroy()
            except Exception:
                pass

        raise

    finally:
        if gpu is not None:
            gpu.destroy()


if __name__ == "__main__":
    main()