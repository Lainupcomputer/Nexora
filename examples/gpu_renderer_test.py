from nexora.rendering.gpu import GPUContext, GPURenderer


def main():
    context = GPUContext(
        1280,
        720,
        "Nexora GPU Renderer",
    )

    renderer = None

    try:
        renderer = GPURenderer(context)

        print("GPU driver:", context.driver)
        print("GPU renderer created")
        print("GPU triangle resources created")
        print("Close the window to exit.")

        renderer.run()

    finally:
        if renderer:
            renderer.destroy()

        context.destroy()


if __name__ == "__main__":
    main()