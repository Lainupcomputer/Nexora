from __future__ import annotations

from nexora.core.engine import Engine


class CameraExample:
    def __init__(self):
        self.engine = None
        self.input = None
        self.window = None
        self.renderer = None

        # Player world position
        self.player_x = 2000.0
        self.player_y = 1500.0

        self.player_size = 48.0
        self.player_speed = 400.0

        # Camera
        self.camera_smooth = 0.12

        # World
        self.world_width = 4000.0
        self.world_height = 3000.0

    # ------------------------------------------------------------------
    # Initialize
    # ------------------------------------------------------------------

    def initialize(self):
        # Movement
        self.input.bind("move_up", "W")
        self.input.bind("move_up", "UP")

        self.input.bind("move_down", "S")
        self.input.bind("move_down", "DOWN")

        self.input.bind("move_left", "A")
        self.input.bind("move_left", "LEFT")

        self.input.bind("move_right", "D")
        self.input.bind("move_right", "RIGHT")

        # Camera
        self.input.bind("zoom_in", "+")
        self.input.bind("zoom_out", "-")
        self.input.bind("camera_reset", "R")
        self.input.bind("camera_shake", "SPACE")

        # Quit
        self.input.bind("quit", "ESCAPE")

        self.renderer.clear_color = (
            20,
            22,
            28,
        )

        camera = self.renderer.camera

        # Start camera at player
        camera.look_at(
            self.player_x,
            self.player_y,
        )

        # World boundaries
        camera.set_bounds(
            0.0,
            self.world_width,
            0.0,
            self.world_height,
        )

        # Dead Zone
        camera.set_dead_zone(
            300.0,
            180.0,
        )

        # Zoom configuration
        camera.min_zoom = 0.25
        camera.max_zoom = 3.0
        camera.zoom_speed = 8.0

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def handle_event(self, event):
        pass

    # ------------------------------------------------------------------
    # Fixed Update
    # ------------------------------------------------------------------

    def fixed_update(self, fixed_delta_time):
        pass

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, delta_time):
        camera = self.renderer.camera

        # --------------------------------------------------------------
        # Quit
        # --------------------------------------------------------------

        if self.input.is_pressed("quit"):
            self.engine.stop()
            return

        # --------------------------------------------------------------
        # Player movement
        # --------------------------------------------------------------

        direction_x = 0.0
        direction_y = 0.0

        if self.input.is_down("move_left"):
            direction_x -= 1.0

        if self.input.is_down("move_right"):
            direction_x += 1.0

        if self.input.is_down("move_up"):
            direction_y -= 1.0

        if self.input.is_down("move_down"):
            direction_y += 1.0

        # Normalize diagonal movement
        if direction_x != 0.0 or direction_y != 0.0:
            length = (
                direction_x * direction_x
                + direction_y * direction_y
            ) ** 0.5

            direction_x /= length
            direction_y /= length

        self.player_x += (
            direction_x
            * self.player_speed
            * delta_time
        )

        self.player_y += (
            direction_y
            * self.player_speed
            * delta_time
        )

        # Keep player inside world
        half_size = self.player_size * 0.5

        self.player_x = max(
            half_size,
            min(
                self.world_width - half_size,
                self.player_x,
            ),
        )

        self.player_y = max(
            half_size,
            min(
                self.world_height - half_size,
                self.player_y,
            ),
        )

        # --------------------------------------------------------------
        # Camera follow
        # --------------------------------------------------------------

        camera.follow(
            self.player_x,
            self.player_y,
            smooth=self.camera_smooth,
            delta_time=delta_time,
        )

        # --------------------------------------------------------------
        # Zoom
        # --------------------------------------------------------------

        if self.input.is_pressed("zoom_in"):
            camera.zoom_by(0.25)

        if self.input.is_pressed("zoom_out"):
            camera.zoom_by(-0.25)

        # --------------------------------------------------------------
        # Screen shake
        # --------------------------------------------------------------

        if self.input.is_pressed("camera_shake"):
            camera.shake(
                strength=25.0,
                duration=0.5,
            )

        # --------------------------------------------------------------
        # Reset camera
        # --------------------------------------------------------------

        if self.input.is_pressed("camera_reset"):
            camera.look_at(
                self.player_x,
                self.player_y,
            )

        # --------------------------------------------------------------
        # Update camera effects
        # --------------------------------------------------------------

        camera.update(
            delta_time
        )

        # --------------------------------------------------------------
        # Camera bounds
        # --------------------------------------------------------------

        camera.clamp(
            self.renderer.width,
            self.renderer.height,
        )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self):
        camera = self.renderer.camera

        # --------------------------------------------------------------
        # World
        # --------------------------------------------------------------

        self.renderer.world_rectangle(
            0,
            0,
            self.world_width,
            self.world_height,
            color=(35, 38, 48),
        )

        # --------------------------------------------------------------
        # Grid
        # --------------------------------------------------------------

        grid_size = 100

        for x in range(
            0,
            int(self.world_width) + 1,
            grid_size,
        ):
            self.renderer.world_line(
                (x, 0),
                (x, self.world_height),
                color=(50, 54, 66),
                width=1,
            )

        for y in range(
            0,
            int(self.world_height) + 1,
            grid_size,
        ):
            self.renderer.world_line(
                (0, y),
                (self.world_width, y),
                color=(50, 54, 66),
                width=1,
            )

        # --------------------------------------------------------------
        # World center
        # --------------------------------------------------------------

        self.renderer.world_circle(
            self.world_width / 2,
            self.world_height / 2,
            30,
            color=(80, 120, 255),
        )

        # --------------------------------------------------------------
        # World objects
        # --------------------------------------------------------------

        objects = [
            (300, 300, 80, (220, 80, 80)),
            (900, 500, 120, (80, 220, 120)),
            (1500, 800, 70, (220, 180, 60)),
            (2300, 400, 100, (180, 80, 220)),
            (3000, 1200, 150, (80, 180, 220)),
            (3500, 2400, 100, (220, 100, 180)),
            (700, 2200, 130, (120, 220, 220)),
            (1800, 2500, 90, (220, 220, 100)),
        ]

        for x, y, size, color in objects:
            self.renderer.world_rectangle(
                x - size / 2,
                y - size / 2,
                size,
                size,
                color=color,
            )

        # --------------------------------------------------------------
        # Player
        # --------------------------------------------------------------

        self.renderer.world_rectangle(
            self.player_x - self.player_size / 2,
            self.player_y - self.player_size / 2,
            self.player_size,
            self.player_size,
            color=(255, 70, 70),
            border_radius=8,
        )

        # Player center
        self.renderer.world_circle(
            self.player_x,
            self.player_y,
            5,
            color=(255, 255, 255),
        )

        # --------------------------------------------------------------
        # Dead Zone visualization
        # --------------------------------------------------------------

        dead_width = camera.dead_zone_width
        dead_height = camera.dead_zone_height

        if dead_width > 0.0 and dead_height > 0.0:
            self.renderer.rectangle(
                self.renderer.width / 2
                - dead_width * camera.zoom / 2,
                self.renderer.height / 2
                - dead_height * camera.zoom / 2,
                dead_width * camera.zoom,
                dead_height * camera.zoom,
                color=(100, 180, 255),
                filled=False,
                thickness=2,
            )

        # --------------------------------------------------------------
        # Screen-space UI
        # --------------------------------------------------------------

        self.renderer.text(
            "Nexora Camera Example",
            20,
            20,
            size=30,
            color=(240, 240, 245),
            bold=True,
        )

        self.renderer.text(
            "WASD / Arrow Keys = Move",
            20,
            60,
            size=22,
            color=(200, 205, 215),
        )

        self.renderer.text(
            "+ / - = Zoom",
            20,
            88,
            size=22,
            color=(200, 205, 215),
        )

        self.renderer.text(
            "SPACE = Screen Shake",
            20,
            116,
            size=22,
            color=(200, 205, 215),
        )

        self.renderer.text(
            "R = Reset Camera",
            20,
            144,
            size=22,
            color=(200, 205, 215),
        )

        self.renderer.text(
            "ESC = Quit",
            20,
            172,
            size=22,
            color=(200, 205, 215),
        )

        # --------------------------------------------------------------
        # Camera information
        # --------------------------------------------------------------

        camera_text = (
            f"Camera: "
            f"{camera.x:.1f}, "
            f"{camera.y:.1f}    "
            f"Zoom: {camera.zoom:.2f}    "
            f"Target: {camera.target_zoom:.2f}"
        )

        self.renderer.text(
            camera_text,
            20,
            self.renderer.height - 35,
            size=20,
            color=(170, 175, 185),
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self):
        pass


def main():
    game = CameraExample()

    engine = Engine(
        game,
        width=1280,
        height=720,
        title="Nexora Engine - Camera",
        target_fps=144,
        fixed_delta_time=1.0 / 60.0,
        resizable=True,
    )

    engine.run()


if __name__ == "__main__":
    main()

