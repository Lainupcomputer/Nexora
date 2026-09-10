import sdl3


def main() -> None:
    print("=== Nexora SDL GPU Probe ===")

    print(f"PySDL3: {sdl3.__version__}")

    if not sdl3.SDL_Init(sdl3.SDL_INIT_VIDEO):
        raise RuntimeError(
            f"SDL_Init failed: {sdl3.SDL_GetError()}"
        )

    print("SDL3 video initialized.")

    try:
        print("\nCreating GPU device...")

        device = sdl3.SDL_CreateGPUDevice(
            sdl3.SDL_GPU_SHADERFORMAT_SPIRV
            | sdl3.SDL_GPU_SHADERFORMAT_DXIL
            | sdl3.SDL_GPU_SHADERFORMAT_MSL,
            True,
            None,
        )

        if not device:
            raise RuntimeError(
                f"SDL_CreateGPUDevice failed: "
                f"{sdl3.SDL_GetError()}"
            )

        print("GPU device created successfully.")

        driver = sdl3.SDL_GetGPUDeviceDriver(device)

        if driver:
            print(f"GPU driver: {driver.decode(errors='replace')}")
        else:
            print("GPU driver: <unknown>")

        sdl3.SDL_DestroyGPUDevice(device)

        print("GPU device destroyed successfully.")

    finally:
        sdl3.SDL_Quit()

    print("\nProbe finished.")


if __name__ == "__main__":
    main()