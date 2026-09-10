from nexora.rendering.gpu import GPUContext, GPUTexture


WIDTH = 128
HEIGHT = 128


def create_test_texture():
    pixels = bytearray(
        WIDTH * HEIGHT * 4
    )

    for y in range(HEIGHT):
        for x in range(WIDTH):
            i = (y * WIDTH + x) * 4

            checker = ((x // 16) + (y // 16)) % 2

            if checker:
                pixels[i + 0] = 255
                pixels[i + 1] = 40
                pixels[i + 2] = 40
                pixels[i + 3] = 255
            else:
                pixels[i + 0] = 40
                pixels[i + 1] = 80
                pixels[i + 2] = 255
                pixels[i + 3] = 255

    return bytes(pixels)


def main():
    context = GPUContext(
        1280,
        720,
        "Nexora GPU Texture Test",
    )

    texture = None

    try:
        data = create_test_texture()

        texture = GPUTexture(
            context.device,
            WIDTH,
            HEIGHT,
            data=data,
        )

        print("GPU driver:", context.driver)
        print("GPU texture created")
        print("Texture size:", texture.width, "x", texture.height)
        print("Texture upload successful")

    finally:
        if texture:
            texture.destroy()

        context.destroy()


if __name__ == "__main__":
    main()