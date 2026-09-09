import pygame


class Window:
    def __init__(
        self,
        width,
        height,
        title,
        resizable=True,
        fullscreen=False,
        vsync=False,
    ):
        self.width = width
        self.height = height
        self.title = title
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.vsync = vsync

        flags = 0

        if self.resizable:
            flags |= pygame.RESIZABLE

        if self.fullscreen:
            flags |= pygame.FULLSCREEN

        self.surface = pygame.display.set_mode(
            (self.width, self.height),
            flags,
            vsync=1 if self.vsync else 0,
        )

        pygame.display.set_caption(self.title)

    def resize(self, width, height):
        self.width = width
        self.height = height

        flags = 0

        if self.resizable:
            flags |= pygame.RESIZABLE

        if self.fullscreen:
            flags |= pygame.FULLSCREEN

        self.surface = pygame.display.set_mode(
            (self.width, self.height),
            flags,
            vsync=1 if self.vsync else 0,
        )

    def set_title(self, title):
        self.title = title
        pygame.display.set_caption(title)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen

        flags = 0

        if self.resizable and not self.fullscreen:
            flags |= pygame.RESIZABLE

        if self.fullscreen:
            flags |= pygame.FULLSCREEN

        self.surface = pygame.display.set_mode(
            (self.width, self.height),
            flags,
            vsync=1 if self.vsync else 0,
        )

    def destroy(self):
        pygame.quit()