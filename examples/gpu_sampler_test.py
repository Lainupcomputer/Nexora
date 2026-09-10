from nexora.rendering.gpu import GPUContext, GPUSampler


def main():
    context = GPUContext(
        1280,
        720,
        "Nexora GPU Sampler Test",
    )

    sampler = None

    try:
        sampler = GPUSampler(
            context.device,
        )

        print("GPU driver:", context.driver)
        print("GPU sampler created")
        print("GPU sampler creation successful")

    finally:
        if sampler:
            sampler.destroy()

        context.destroy()


if __name__ == "__main__":
    main()