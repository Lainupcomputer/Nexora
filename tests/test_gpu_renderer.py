from __future__ import annotations


class DummySpriteBatch:
    def __init__(self) -> None:
        self.begin_calls = 0
        self.added = 0
        self.texture = None

    def begin(
        self,
        texture,
    ) -> None:
        self.begin_calls += 1
        self.texture = texture
        self.added = 0

    def add_many(
        self,
        sprites,
        *,
        workers=None,
    ) -> int:
        count = len(
            sprites
        )

        self.added += count

        return count


class DummyRenderer:
    def __init__(self) -> None:
        self._frame_started = True
        self._active_texture = None

        self.sprite_batch = (
            DummySpriteBatch()
        )

    def _require_frame(
        self,
    ) -> None:
        if not self._frame_started:
            raise RuntimeError

    def _set_texture(
        self,
        texture,
    ) -> None:
        if self._active_texture is texture:
            return

        if self._active_texture is not None:
            raise RuntimeError(
                "Multiple textures are not supported."
            )

        self._active_texture = texture

        self.sprite_batch.begin(
            texture
        )

    def sprites(
        self,
        texture,
        sprites,
        *,
        workers=None,
    ) -> int:
        self._require_frame()

        if texture is None:
            return 0

        if not hasattr(
            sprites,
            "__len__",
        ):
            sprites = list(
                sprites
            )

        if not sprites:
            return 0

        self._set_texture(
            texture
        )

        return self.sprite_batch.add_many(
            sprites,
            workers=workers,
        )


def test_sprites_appends_to_existing_batch():
    renderer = DummyRenderer()

    texture = object()

    first = [
        (
            0.0,
            0.0,
            32.0,
            32.0,
            0.0,
            0.5,
            0.5,
            1.0,
            False,
            False,
            0.0,
            0.0,
            0.25,
            0.25,
        ),
    ]

    second = [
        (
            32.0,
            0.0,
            32.0,
            32.0,
            0.0,
            0.5,
            0.5,
            1.0,
            False,
            False,
            0.25,
            0.0,
            0.25,
            0.25,
        ),
        (
            64.0,
            0.0,
            32.0,
            32.0,
            0.0,
            0.5,
            0.5,
            1.0,
            False,
            False,
            0.5,
            0.0,
            0.25,
            0.25,
        ),
    ]

    first_count = renderer.sprites(
        texture,
        first,
    )

    second_count = renderer.sprites(
        texture,
        second,
    )

    assert first_count == 1
    assert second_count == 2

    # Important:
    # begin() must only happen once for the same texture.
    assert (
        renderer.sprite_batch.begin_calls
        == 1
    )

    # All sprites must remain in the batch.
    assert (
        renderer.sprite_batch.added
        == 3
    )