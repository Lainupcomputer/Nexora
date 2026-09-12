from __future__ import annotations

from nexora.rendering.camera import Camera
from nexora.rendering.gpu import (
    GPURenderer,
    RenderSnapshot,
)


class Renderer:
    """
    Public Nexora renderer.

    Nexora is GPU-first.

    The renderer owns the public 2D camera. The same Camera
    instance is passed down into the GPU renderer and finally
    used by the GPU sprite batch.
    """

    def __init__(
        self,
        gpu_context,
        *,
        max_sprites: int = 10000,
        workers: int = 4,
        camera: Camera | None = None,
        font=None,
    ) -> None:
        self.camera = (
            camera
            if camera is not None
            else Camera()
        )

        self.gpu = GPURenderer(
            gpu_context,
            max_sprites=max_sprites,
            workers=workers,
            camera=self.camera,
            font=font,
        )

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        color=(1.0, 1.0, 1.0, 1.0),
        rotation: float = 0.0,
        origin=(0.5, 0.5),
        radius: float = 0.0,
    ) -> None:
        self.gpu.rect(
            x,
            y,
            width,
            height,
            color=color,
            rotation=rotation,
            origin=origin,
            radius=radius,
        )

    def text(
        self,
        *args,
        **kwargs,
    ):
        return self.gpu.text(
            *args,
            **kwargs,
        )

    def text_measure(
        self,
        text: str,
        *,
        scale: float = 1.0,
    ) -> tuple[float, float]:
        return self.gpu.text_measure(
            text,
            scale=scale,
        )

    def text_baseline(
        self,
        *,
        scale: float = 1.0,
    ) -> float:
        return self.gpu.text_baseline(
            scale=scale,
        )

    @property
    def width(self) -> int:
        return self.gpu.width

    @property
    def height(self) -> int:
        return self.gpu.height

    @property
    def driver(self) -> str:
        return self.gpu.driver

    def begin_frame(self) -> bool:
        return self.gpu.begin_frame()

    def end_frame(self) -> bool:
        return self.gpu.end_frame()

    def sprite(
        self,
        texture,
        x: float,
        y: float,
        *,
        width: float,
        height: float,
        rotation: float = 0.0,
        origin=(0.5, 0.5),
        alpha: float = 1.0,
        flip_x: bool = False,
        flip_y: bool = False,
        uv=(0.0, 0.0, 1.0, 1.0),
    ) -> None:
        self.gpu.sprite(
            texture,
            x,
            y,
            width=width,
            height=height,
            rotation=rotation,
            origin=origin,
            alpha=alpha,
            flip_x=flip_x,
            flip_y=flip_y,
            uv=uv,
        )

    def sprites(
        self,
        texture,
        sprites,
        *,
        workers: int | None = None,
    ) -> int:
        return self.gpu.sprites(
            texture,
            sprites,
            workers=workers,
        )

    def submit(
        self,
        snapshot: RenderSnapshot,
        texture,
    ) -> int:
        return self.gpu.submit(
            snapshot,
            texture,
        )

    def resize(
        self,
        width: int,
        height: int,
    ) -> None:
        self.gpu.resize(
            width,
            height,
        )

    def destroy(self) -> None:
        self.gpu.destroy()