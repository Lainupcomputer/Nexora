from __future__ import annotations

import sdl3

from nexora.core.game import Game
from nexora.nodes import CharacterBody2D
from nexora.rendering.gpu.texture import GPUTexture
from nexora.scene import Scene
from nexora.tilemap import (
    TileCollision,
    TileMap,
    TileSet,
)


class CharacterBodyTest(Game):
    # ==============================================================
    # Map
    # ==============================================================

    TILE_SIZE = 64

    MAP_WIDTH = 20
    MAP_HEIGHT = 12

    # ==============================================================
    # Player
    # ==============================================================

    PLAYER_WIDTH = 36.0
    PLAYER_HEIGHT = 52.0

    MOVE_SPEED = 260.0

    # ==============================================================
    # Platformer physics
    # ==============================================================

    GRAVITY = 1200.0
    JUMP_FORCE = 520.0

    MAX_FALL_SPEED = 900.0

    def __init__(
        self,
    ) -> None:
        super().__init__()

        # ==========================================================
        # Scene
        # ==========================================================

        self.scene = Scene(
            "CharacterBody2DTest"
        )

        # ==========================================================
        # Resources
        # ==========================================================

        self.texture: GPUTexture | None = None

        self.tilemap: TileMap | None = None
        self.tileset: TileSet | None = None
        self.collision: TileCollision | None = None

        # ==========================================================
        # Player
        # ==========================================================

        self.player: CharacterBody2D | None = None

        # ==========================================================
        # Debug state
        # ==========================================================

        self._last_on_floor = False
        self._last_on_wall = False
        self._last_on_ceiling = False

    # ==============================================================
    # Render offset
    # ==============================================================

    @property
    def map_offset_x(
        self,
    ) -> float:
        """
        TileCollision uses map coordinates with (0, 0) at the
        top-left of the map.

        Nexora rendering uses (0, 0) at the center of the screen.

        This offset centers the complete map around Nexora's
        world origin.
        """

        return -(
            self.MAP_WIDTH
            * self.TILE_SIZE
        ) / 2.0

    @property
    def map_offset_y(
        self,
    ) -> float:
        return -(
            self.MAP_HEIGHT
            * self.TILE_SIZE
        ) / 2.0

    # ==============================================================
    # Initialize
    # ==============================================================

    def initialize(
        self,
    ) -> None:
        print("=" * 60)
        print(" Nexora CharacterBody2D Platformer Test")
        print("=" * 60)
        print()

        # ----------------------------------------------------------
        # TileSet
        # ----------------------------------------------------------

        self.tileset = TileSet(
            name="CollisionTiles",
            columns=2,
            rows=1,
            tile_width=self.TILE_SIZE,
            tile_height=self.TILE_SIZE,
        )

        # Tile 0 is solid.

        self.tileset.metadata(
            0
        ).solid = True

        # Tile 1 is intentionally non-solid.

        self.tileset.metadata(
            1
        ).solid = False

        # ----------------------------------------------------------
        # Texture
        # ----------------------------------------------------------

        texture_width = (
            self.TILE_SIZE
            * 2
        )

        texture_height = (
            self.TILE_SIZE
        )

        pixels = (
            self._create_tileset_pixels()
        )

        self.texture = GPUTexture(
            self.engine.gpu_context.device,
            texture_width,
            texture_height,
            data=pixels,
            bytes_per_pixel=4,
        )

        # ----------------------------------------------------------
        # TileMap
        # ----------------------------------------------------------

        self.tilemap = TileMap(
            name="CollisionMap",
            width=self.MAP_WIDTH,
            height=self.MAP_HEIGHT,
            tile_width=self.TILE_SIZE,
            tile_height=self.TILE_SIZE,
        )

        collision_layer = (
            self.tilemap.create_layer(
                "collision"
            )
        )

        # ==========================================================
        # Floor
        # ==========================================================

        floor_y = (
            self.MAP_HEIGHT
            - 2
        )

        for x in range(
            self.MAP_WIDTH
        ):
            collision_layer.set_tile(
                x,
                floor_y,
                0,
            )

        # ==========================================================
        # Left wall
        # ==========================================================

        for y in range(
            3,
            floor_y
        ):
            collision_layer.set_tile(
                3,
                y,
                0,
            )

        # ==========================================================
        # Right wall
        # ==========================================================

        for y in range(
            5,
            floor_y
        ):
            collision_layer.set_tile(
                14,
                y,
                0,
            )

        # ==========================================================
        # Floating platform
        # ==========================================================

        for x in range(
            7,
            11,
        ):
            collision_layer.set_tile(
                x,
                7,
                0,
            )

        # ==========================================================
        # Second platform
        # ==========================================================

        for x in range(
            11,
            14,
        ):
            collision_layer.set_tile(
                x,
                5,
                0,
            )

        # ==========================================================
        # Ceiling test
        # ==========================================================

        for x in range(
            5,
            8,
        ):
            collision_layer.set_tile(
                x,
                3,
                0,
            )

        # ----------------------------------------------------------
        # Collision
        # ----------------------------------------------------------

        self.collision = TileCollision(
            self.tilemap,
            self.tileset,
        )

        # ----------------------------------------------------------
        # Character
        # ----------------------------------------------------------

        player = (
            self.scene.create_node(
                "Player",
                node_type=CharacterBody2D,
            )
        )

        assert isinstance(
            player,
            CharacterBody2D,
        )

        self.player = player

        self.player.set_collision_size(
            self.PLAYER_WIDTH,
            self.PLAYER_HEIGHT,
        )

        # Spawn above the floor.

        self.player.transform.x = (
            6
            * self.TILE_SIZE
        )

        self.player.transform.y = (
            6
            * self.TILE_SIZE
        )

        # ----------------------------------------------------------
        # Information
        # ----------------------------------------------------------

        print(
            "Controls:"
        )

        print(
            "  A / LEFT   -> move left"
        )

        print(
            "  D / RIGHT  -> move right"
        )

        print(
            "  SPACE      -> jump"
        )

        print(
            "  R          -> reset player"
        )

        print(
            "  ESC        -> close"
        )

        print()

        print(
            "Physics:"
        )

        print(
            f"  Move speed:     {self.MOVE_SPEED}"
        )

        print(
            f"  Gravity:        {self.GRAVITY}"
        )

        print(
            f"  Jump force:     {self.JUMP_FORCE}"
        )

        print(
            f"  Max fall speed: {self.MAX_FALL_SPEED}"
        )

        print()

        print(
            "Expected:"
        )

        print(
            "  Player falls automatically."
        )

        print(
            "  Player stops on floor and platforms."
        )

        print(
            "  SPACE jumps only while standing on the floor."
        )

        print(
            "  Player cannot pass through walls."
        )

        print(
            "  Player should slide along walls."
        )

        print(
            "  Jumping into a ceiling should stop upward movement."
        )

        print()

    # ==============================================================
    # Generated texture
    # ==============================================================

    def _create_tileset_pixels(
        self,
    ) -> bytes:
        width = (
            self.TILE_SIZE
            * 2
        )

        height = (
            self.TILE_SIZE
        )

        pixels = bytearray(
            width
            * height
            * 4
        )

        for y in range(
            height
        ):
            for x in range(
                width
            ):
                tile = (
                    x
                    // self.TILE_SIZE
                )

                # --------------------------------------------------
                # Base color
                # --------------------------------------------------

                if tile == 0:
                    r = 90
                    g = 90
                    b = 100
                    a = 255

                else:
                    r = 50
                    g = 130
                    b = 80
                    a = 255

                local_x = (
                    x
                    % self.TILE_SIZE
                )

                local_y = y

                # --------------------------------------------------
                # Border
                # --------------------------------------------------

                if (
                    local_x < 2
                    or local_y < 2
                    or local_x
                    >= self.TILE_SIZE - 2
                    or local_y
                    >= self.TILE_SIZE - 2
                ):
                    r = 230
                    g = 230
                    b = 230

                # --------------------------------------------------
                # Inner marker
                # --------------------------------------------------

                if (
                    20
                    <= local_x
                    < 44
                    and
                    20
                    <= local_y
                    < 44
                ):
                    r = max(
                        0,
                        r - 35,
                    )

                    g = max(
                        0,
                        g - 35,
                    )

                    b = max(
                        0,
                        b - 35,
                    )

                # --------------------------------------------------
                # RGBA
                # --------------------------------------------------

                offset = (
                    (
                        y
                        * width
                        + x
                    )
                    * 4
                )

                pixels[
                    offset
                ] = r

                pixels[
                    offset + 1
                ] = g

                pixels[
                    offset + 2
                ] = b

                pixels[
                    offset + 3
                ] = a

        return bytes(
            pixels
        )

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        super().update(
            delta_time
        )

        if (
            self.player is None
            or self.collision is None
        ):
            return

        # ==========================================================
        # Horizontal input
        # ==========================================================

        move_x = 0.0

        if (
            self.input.key_down(
                "A"
            )
            or self.input.key_down(
                "LEFT"
            )
        ):
            move_x -= 1.0

        if (
            self.input.key_down(
                "D"
            )
            or self.input.key_down(
                "RIGHT"
            )
        ):
            move_x += 1.0

        self.player.velocity.x = (
            move_x
            * self.MOVE_SPEED
        )

        # ==========================================================
        # Jump
        # ==========================================================

        if (
            self.player.is_on_floor
            and self.input.key_pressed(
                "SPACE"
            )
        ):
            self.player.velocity.y = (
                -self.JUMP_FORCE
            )

            print(
                "[CharacterBody2D] jump"
            )

        # ==========================================================
        # Gravity
        # ==========================================================

        self.player.velocity.y += (
            self.GRAVITY
            * delta_time
        )

        if (
            self.player.velocity.y
            > self.MAX_FALL_SPEED
        ):
            self.player.velocity.y = (
                self.MAX_FALL_SPEED
            )

        # ==========================================================
        # Move + collision
        # ==========================================================

        self.player.move_and_slide(
            self.collision,
            "collision",
            delta_time,
        )

        # ==========================================================
        # Debug collision-state changes
        # ==========================================================

        if (
            self.player.is_on_floor
            != self._last_on_floor
        ):
            print(
                "[CharacterBody2D] "
                f"floor = "
                f"{self.player.is_on_floor}"
            )

            self._last_on_floor = (
                self.player.is_on_floor
            )

        if (
            self.player.is_on_wall
            != self._last_on_wall
        ):
            print(
                "[CharacterBody2D] "
                f"wall = "
                f"{self.player.is_on_wall}"
            )

            self._last_on_wall = (
                self.player.is_on_wall
            )

        if (
            self.player.is_on_ceiling
            != self._last_on_ceiling
        ):
            print(
                "[CharacterBody2D] "
                f"ceiling = "
                f"{self.player.is_on_ceiling}"
            )

            self._last_on_ceiling = (
                self.player.is_on_ceiling
            )

    # ==============================================================
    # Render
    # ==============================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        super().render(
            interpolation
        )

        if (
            self.player is None
            or self.tilemap is None
            or self.tileset is None
            or self.texture is None
        ):
            return

        # ==========================================================
        # Render collision map
        # ==========================================================

        layer = (
            self.tilemap.require_layer(
                "collision"
            )
        )

        for (
            x,
            y,
            tile_id,
        ) in layer.iter_tiles():
            world_x = (
                self.map_offset_x
                + x
                * self.TILE_SIZE
                + self.TILE_SIZE
                / 2.0
            )

            world_y = (
                self.map_offset_y
                + y
                * self.TILE_SIZE
                + self.TILE_SIZE
                / 2.0
            )

            uv = (
                self.tileset.uv(
                    tile_id
                )
            )

            self.renderer.sprite(
                self.texture,
                world_x,
                world_y,
                width=float(
                    self.TILE_SIZE
                ),
                height=float(
                    self.TILE_SIZE
                ),
                uv=uv,
            )

        # ==========================================================
        # Render player
        # ==========================================================

        player_x = (
            self.map_offset_x
            + self.player.transform.x
            + self.player.collision_width
            / 2.0
        )

        player_y = (
            self.map_offset_y
            + self.player.transform.y
            + self.player.collision_height
            / 2.0
        )

        # ----------------------------------------------------------
        # Change player color depending on collision state.
        # ----------------------------------------------------------

        if self.player.is_on_floor:
            color = (
                0.2,
                0.9,
                0.3,
                1.0,
            )

        elif self.player.is_on_wall:
            color = (
                0.9,
                0.7,
                0.2,
                1.0,
            )

        elif self.player.is_on_ceiling:
            color = (
                0.7,
                0.3,
                0.9,
                1.0,
            )

        else:
            color = (
                0.9,
                0.2,
                0.2,
                1.0,
            )

        self.renderer.rect(
            player_x,
            player_y,
            self.player.collision_width,
            self.player.collision_height,
            color=color,
        )

    # ==============================================================
    # Events
    # ==============================================================

    def handle_event(
        self,
        event,
    ) -> None:
        if (
            event.type
            != sdl3.SDL_EVENT_KEY_DOWN
        ):
            return

        if getattr(
            event.key,
            "repeat",
            False,
        ):
            return

        key = (
            event.key.key
        )

        # ----------------------------------------------------------
        # Exit
        # ----------------------------------------------------------

        if key == sdl3.SDLK_ESCAPE:
            self.stop()

            return

        # ----------------------------------------------------------
        # Reset
        # ----------------------------------------------------------

        if (
            key == sdl3.SDLK_R
            and self.player is not None
        ):
            self.player.transform.x = (
                6
                * self.TILE_SIZE
            )

            self.player.transform.y = (
                6
                * self.TILE_SIZE
            )

            self.player.velocity.clear()

            print(
                "[CharacterBody2D] reset"
            )

    # ==============================================================
    # Shutdown
    # ==============================================================

    def shutdown(
        self,
    ) -> None:
        if self.texture is not None:
            self.texture.destroy()

            self.texture = None

        super().shutdown()


def main() -> None:
    game = CharacterBodyTest()

    game.run()


if __name__ == "__main__":
    main()