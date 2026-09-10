import time

from nexora.rendering.gpu import GPUContext


def main():
    gpu = GPUContext(
        1280,
        720,
        "Nexora GPU Context",
    )

    print("GPU initialized")
    print("Driver:", gpu.driver)
    print("Swapchain format:", gpu.swapchain_format)

    try:
        running = True

        while running:
            for event in gpu.poll_events():
                if event.type == 0x100:
                    running = False

            if gpu.begin_frame():
                render_pass = gpu.begin_render_pass(
                    (0.03, 0.03, 0.05, 1.0)
                )

                gpu.end_render_pass(render_pass)
                gpu.end_frame()

            time.sleep(0.001)

    finally:
        gpu.destroy()


if __name__ == "__main__":
    main()