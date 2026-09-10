from __future__ import annotations

import sdl3

from nexora.threading.context import ThreadContext
from nexora.debug.logger import Logger


def main() -> None:
    ThreadContext.initialize()

    logger = Logger()

    if not sdl3.SDL_Init(sdl3.SDL_INIT_VIDEO):
        raise RuntimeError(
            f"SDL_Init failed: {sdl3.SDL_GetError()}"
        )

    window = None
    device = None

    try:
        logger.info("Creating SDL3 window...")

        window = sdl3.SDL_CreateWindow(
            b"Nexora GPU Test",
            1280,
            720,
            sdl3.SDL_WINDOW_RESIZABLE,
        )

        if not window:
            raise RuntimeError(
                "SDL_CreateWindow failed: "
                f"{sdl3.SDL_GetError()}"
            )

        logger.info(
            "SDL3 window created successfully."
        )

        logger.info("Creating GPU device...")

        shader_formats = (
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
            | sdl3.SDL_GPU_SHADERFORMAT_DXIL
            | sdl3.SDL_GPU_SHADERFORMAT_MSL
        )

        device = sdl3.SDL_CreateGPUDevice(
            shader_formats,
            False,
            None,
        )

        if not device:
            raise RuntimeError(
                "SDL_CreateGPUDevice failed: "
                f"{sdl3.SDL_GetError()}"
            )

        logger.info(
            "GPU device created successfully."
        )

        driver = sdl3.SDL_GetGPUDeviceDriver(
            device
        )

        if isinstance(driver, bytes):
            driver = driver.decode(
                "utf-8",
                errors="replace",
            )

        logger.info(
            f"GPU driver: {driver}"
        )

        logger.info(
            "Claiming SDL3 window for GPU..."
        )

        if not sdl3.SDL_ClaimWindowForGPUDevice(
            device,
            window,
        ):
            raise RuntimeError(
                "SDL_ClaimWindowForGPUDevice failed: "
                f"{sdl3.SDL_GetError()}"
            )

        logger.info(
            "SDL3 window successfully claimed by GPU."
        )

        running = True

        while running:

            event = sdl3.SDL_Event()

            while sdl3.SDL_PollEvent(
                event
            ):
                if event.type == sdl3.SDL_EVENT_QUIT:
                    running = False

                elif (
                    event.type
                    == sdl3.SDL_EVENT_KEY_DOWN
                ):
                    if (
                        event.key.key
                        == sdl3.SDLK_ESCAPE
                    ):
                        running = False

            sdl3.SDL_Delay(10)

        logger.info(
            "GPU window test finished."
        )

    finally:

        if device is not None:

            if window is not None:
                sdl3.SDL_ReleaseWindowFromGPUDevice(
                    device,
                    window,
                )

            sdl3.SDL_WaitForGPUIdle(
                device
            )

            sdl3.SDL_DestroyGPUDevice(
                device
            )

        if window is not None:
            sdl3.SDL_DestroyWindow(
                window
            )

        sdl3.SDL_Quit()


if __name__ == "__main__":
    main()