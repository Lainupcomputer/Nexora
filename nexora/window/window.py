from __future__ import annotations

import sdl3


class Window:
    """
    Public SDL3 window abstraction for Nexora.

    The actual SDL window is owned by GPUContext.
    This class only provides the high-level window API.
    """

    def __init__(
        self,
        gpu_context,
        *,
        resizable: bool = True,
        fullscreen: bool = False,
    ) -> None:
        self.gpu_context = gpu_context

        self.resizable = bool(resizable)
        self.fullscreen = bool(fullscreen)

        self.width = int(gpu_context.width)
        self.height = int(gpu_context.height)
        self.title = str(gpu_context.title)

        self._destroyed = False

        if self.resizable:
            self._set_resizable(True)

        if self.fullscreen:
            self._set_fullscreen(True)

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def handle(self):
        """Return the underlying SDL3 window pointer."""
        return self.gpu_context.window

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height

    # ==========================================================
    # INTERNAL
    # ==========================================================

    def _require_window(self):
        if self._destroyed:
            raise RuntimeError("Window has been destroyed")

        if self.gpu_context.window is None:
            raise RuntimeError("SDL window is not available")

        return self.gpu_context.window

    def _set_resizable(self, enabled: bool) -> None:
        window = self._require_window()

        if hasattr(sdl3, "SDL_SetWindowResizable"):
            sdl3.SDL_SetWindowResizable(
                window,
                bool(enabled),
            )

    def _set_fullscreen(self, enabled: bool) -> None:
        window = self._require_window()

        flags = (
            sdl3.SDL_WINDOW_FULLSCREEN
            if enabled
            else 0
        )

        if not sdl3.SDL_SetWindowFullscreen(
            window,
            flags,
        ):
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"SDL_SetWindowFullscreen failed: {error}"
            )

    # ==========================================================
    # WINDOW CONTROL
    # ==========================================================

    def resize(
        self,
        width: int,
        height: int,
    ) -> None:
        window = self._require_window()

        width = max(1, int(width))
        height = max(1, int(height))

        if not sdl3.SDL_SetWindowSize(
            window,
            width,
            height,
        ):
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"SDL_SetWindowSize failed: {error}"
            )

        self.width = width
        self.height = height

        self.gpu_context.width = width
        self.gpu_context.height = height

    def set_title(self, title: str) -> None:
        window = self._require_window()

        title = str(title)

        if not sdl3.SDL_SetWindowTitle(
            window,
            title.encode("utf-8"),
        ):
            error = sdl3.SDL_GetError()

            if isinstance(error, bytes):
                error = error.decode(
                    "utf-8",
                    errors="replace",
                )

            raise RuntimeError(
                f"SDL_SetWindowTitle failed: {error}"
            )

        self.title = title
        self.gpu_context.title = title

    def toggle_fullscreen(self) -> None:
        self._set_fullscreen(
            not self.fullscreen
        )

        self.fullscreen = not self.fullscreen

    # ==========================================================
    # STATE
    # ==========================================================

    def set_resizable(self, enabled: bool) -> None:
        enabled = bool(enabled)

        self._set_resizable(enabled)
        self.resizable = enabled

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def destroy(self) -> None:
        """
        Window destruction is owned by GPUContext.

        We intentionally do not call SDL_Quit() here.
        """

        if self._destroyed:
            return

        self._destroyed = True

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.destroy()