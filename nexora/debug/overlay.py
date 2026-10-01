from __future__ import annotations

import platform
import sys
import sysconfig

from nexora.debug.metrics import DebugMetrics
from nexora.debug.physics import (
    PhysicsDebugRenderer,
)


class DebugOverlay:
    """
    Global Nexora F3 debug overlay.

    The overlay belongs directly to the Engine instead of a Scene
    or UIRoot.

    It is intended to be rendered as the final engine overlay.
    """

    def __init__(
        self,
        engine,
    ) -> None:
        self.engine = engine

        self.visible = False
        self.audio_visible = False

        self.metrics = (
            DebugMetrics()
        )

        # ======================================================
        # Physics debug
        # ======================================================

        self.physics = (
            PhysicsDebugRenderer()
        )

        # ======================================================
        # Appearance
        # ======================================================
        #
        # Larger than the previous debug overlay.
        # ======================================================

        self.text_scale = 1.05

        self.margin = 16.0
        self.line_spacing = 5.0

    # ==========================================================
    # VISIBILITY
    # ==========================================================

    def toggle(
        self,
    ) -> bool:
        self.visible = (
            not self.visible
        )

        return self.visible

    def show(
        self,
    ) -> None:
        self.visible = True

    def hide(
        self,
    ) -> None:
        self.visible = False

    def toggle_audio(
        self,
    ) -> bool:
        self.audio_visible = (
            not self.audio_visible
        )

        return self.audio_visible

    def show_audio(
        self,
    ) -> None:
        self.audio_visible = True

    def hide_audio(
        self,
    ) -> None:
        self.audio_visible = False

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not (
            self.visible
            or self.audio_visible
        ):
            return

        self.metrics.update(
            delta_time
        )

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        renderer,
    ) -> None:
        # ======================================================
        # Physics debug
        # ======================================================

        if self.physics.visible:
            scene = getattr(
                self.engine.game,
                "scene",
                None,
            )

            if scene is not None:
                self.physics.render(
                    renderer,
                    scene.root,
                )

        # ======================================================
        # Debug information overlay
        # ======================================================

        if not (
            self.visible
            or self.audio_visible
        ):
            return

        if self.visible:
            left_lines = (
                self._build_left_lines()
            )

            right_lines = (
                self._build_right_lines(
                    renderer
                )
            )

            self._draw_left(
                renderer,
                left_lines,
            )

            self._draw_right(
                renderer,
                right_lines,
            )

        if self.audio_visible:
            audio_lines = (
                self._build_audio_mixer_lines()
            )

            self._draw_audio_mixer_bottom_left(
                renderer,
                audio_lines,
            )

    # ==========================================================
    # LEFT SIDE
    # ==========================================================

    def _build_left_lines(
        self,
    ) -> list[str]:
        data = (
            self.metrics.snapshot
        )

        # ------------------------------------------------------
        # Time
        # ------------------------------------------------------

        time_system = (
            self.engine.time
        )

        fixed_delta = float(
            time_system.fixed_delta_time
        )

        fixed_fps = (
            1.0 / fixed_delta
            if fixed_delta > 0.0
            else 0.0
        )

        target_fps = int(
            self.engine.loop.target_fps
        )

        # ------------------------------------------------------
        # RAM
        # ------------------------------------------------------

        if (
            data.ram_used_mb
            >= 1024.0
        ):
            ram_text = (
                f"{data.ram_used_mb / 1024.0:.2f} GB"
            )

        else:
            ram_text = (
                f"{data.ram_used_mb:.0f} MB"
            )

        # ------------------------------------------------------
        # Scene
        # ------------------------------------------------------

        scene = getattr(
            self.engine.game,
            "scene",
            None,
        )

        scene_name = (
            scene.name
            if scene is not None
            else "<none>"
        )

        lines = [
            (
                "FPS: "
                f"{data.fps:.0f} / "
                f"{target_fps}"
            ),

            (
                "Frame time: "
                f"{data.frame_time_ms:.2f} ms"
            ),

            (
                "Delta: "
                f"{data.delta_time:.4f} s"
            ),

            (
                "Tickrate: "
                f"{fixed_fps:.0f}"
            ),

            "",

            (
                "CPU: "
                f"{data.cpu_percent:.1f} %"
            ),

            (
                "RAM: "
                f"{ram_text}"
            ),

            "",

            (
                "Scene: "
                f"{scene_name}"
            ),
        ]

        return lines

    # ==========================================================
    # AUDIO MIXER DEBUG
    # ==========================================================

    def _build_audio_mixer_lines(
        self,
    ) -> list[str]:
        """Build a compact, read-only live view of Nexora's audio mixer."""

        audio = getattr(
            self.engine,
            "audio",
            None,
        )

        if audio is None:
            return []

        try:
            buses = tuple(
                audio.get_buses()
            )
        except Exception:
            return [
                "",
                "Audio Mixer",
                "------------------------",
                "Unavailable",
            ]

        player = getattr(
            audio,
            "player",
            None,
        )

        device = getattr(
            audio,
            "device",
            None,
        )

        # ------------------------------------------------------
        # Sources / sends / device queue
        # ------------------------------------------------------

        try:
            source_count = len(
                player.sources
            ) if player is not None else 0
        except Exception:
            source_count = 0

        try:
            send_count = len(
                audio.get_sends()
            )
        except Exception:
            send_count = 0

        queue_text = "N/A"

        if (
            device is not None
            and getattr(
                device,
                "initialized",
                False,
            )
        ):
            try:
                queued_frames = int(
                    device.queued_frames()
                )

                frequency = int(
                    getattr(
                        device,
                        "frequency",
                        0,
                    )
                )

                if frequency > 0:
                    queue_ms = (
                        queued_frames
                        / frequency
                        * 1000.0
                    )

                    queue_text = (
                        f"{queue_ms:.1f} ms"
                    )

                else:
                    queue_text = (
                        f"{queued_frames} frames"
                    )

            except Exception:
                queue_text = "N/A"

        lines = [
            "",
            "Audio Mixer",
            "------------------------",
            (
                f"Sources: {source_count}   "
                f"Buses: {len(buses)}   "
                f"Sends: {send_count}"
            ),
            (
                "Queue: "
                f"{queue_text}"
            ),
        ]

        if not buses:
            lines.append(
                "No buses"
            )
            return lines

        # ------------------------------------------------------
        # Keep the debug overlay compact. Master is always first,
        # followed by the hierarchy in mixer order.
        # ------------------------------------------------------

        max_buses = 8
        visible_buses = buses[:max_buses]

        for bus in visible_buses:
            try:
                peak_left, peak_right = (
                    bus.peak_dbfs
                )
            except Exception:
                peak_left = peak_right = float(
                    "-inf"
                )

            depth = self._audio_bus_depth(
                bus
            )

            indent = "  " * min(
                depth,
                4,
            )

            flags: list[str] = []

            if getattr(
                bus,
                "muted",
                False,
            ):
                flags.append("M")

            if getattr(
                bus,
                "solo",
                False,
            ):
                flags.append("S")

            if getattr(
                bus,
                "clipped",
                False,
            ):
                flags.append("CLIP")

            state = (
                "[" + " ".join(flags) + "]"
                if flags
                else ""
            )

            effect_count = len(
                getattr(
                    bus,
                    "effects",
                    (),
                )
            )

            outgoing_sends = 0
            try:
                outgoing_sends = sum(
                    1
                    for send in audio.get_sends()
                    if getattr(
                        send,
                        "source_bus_id",
                        None,
                    ) == bus.id
                )
            except Exception:
                outgoing_sends = 0

            lines.append(
                (
                    f"{indent}{bus.name}: "
                    f"V {bus.volume:.2f}  "
                    f"P {bus.pan:+.2f}  "
                    f"FX {effect_count}  "
                    f"Send {outgoing_sends}"
                    f" {state}"
                ).rstrip()
            )

        hidden = (
            len(buses)
            - len(visible_buses)
        )

        if hidden > 0:
            lines.append(
                f"... +{hidden} buses"
            )

        return lines

    @staticmethod
    def _audio_bus_depth(
        bus,
    ) -> int:
        depth = 0
        current = getattr(
            bus,
            "parent",
            None,
        )
        seen: set[int] = set()

        while current is not None:
            identity = id(
                current
            )

            if identity in seen:
                break

            seen.add(
                identity
            )
            depth += 1
            current = getattr(
                current,
                "parent",
                None,
            )

        return depth

    @staticmethod
    def _format_dbfs(
        value: float,
    ) -> str:
        if value == float(
            "-inf"
        ):
            return "-inf"

        if value < -99.9:
            return "<-99"

        return f"{value:.1f}"


    # ==========================================================
    # AUDIO MIXER BOTTOM-LEFT
    # ==========================================================

    def _draw_audio_mixer_bottom_left(
        self,
        renderer,
        lines: list[str],
    ) -> None:
        """Draw the complete audio debug block anchored to the bottom-left."""

        if not lines:
            return

        half_width = renderer.width * 0.5
        half_height = renderer.height * 0.5
        line_height = self._line_height(renderer)
        baseline = renderer.text_baseline(scale=self.text_scale)

        # Keep the complete block inside the viewport regardless of the
        # amount of regular debug text shown at the top-left.
        block_height = max(0.0, (len(lines) - 1) * line_height) + baseline
        x = -half_width + self.margin
        y = half_height - self.margin - block_height + baseline

        bus_row_indices: list[int] = []
        try:
            mixer_index = lines.index("Audio Mixer")
            first_bus_index = mixer_index + 4
            audio = getattr(self.engine, "audio", None)
            buses = tuple(audio.get_buses())[:8] if audio is not None else ()
            bus_row_indices = [first_bus_index + i for i in range(len(buses))]
        except Exception:
            buses = ()

        for index, line in enumerate(lines):
            if line:
                renderer.text(
                    line,
                    x,
                    y + index * line_height,
                    scale=self.text_scale,
                )

        if not buses:
            return

        # Meters sit on the right edge of the left half, but stay vertically
        # aligned with the bus text rows in this bottom-left block.
        meter_width = max(
            120.0,
            min(260.0, half_width * 0.30),
        )
        meter_x = -self.margin - meter_width
        meter_height = max(
            3.0,
            min(5.0, line_height * 0.22),
        )
        channel_gap = 2.0

        for bus, row_index in zip(buses, bus_row_indices):
            row_y = y + row_index * line_height
            top = row_y - baseline + 2.0

            try:
                peak_left, peak_right = bus.peak_dbfs
            except Exception:
                peak_left = peak_right = float("-inf")

            try:
                hold_left, hold_right = bus.peak_hold_dbfs
            except Exception:
                hold_left = peak_left
                hold_right = peak_right

            clipped = bool(getattr(bus, "clipped", False))

            self._draw_stereo_meter_channel(
                renderer, meter_x, top, meter_width, meter_height,
                peak_left, hold_left, clipped, "L",
            )
            self._draw_stereo_meter_channel(
                renderer, meter_x, top + meter_height + channel_gap,
                meter_width, meter_height, peak_right, hold_right, clipped, "R",
            )

    def _draw_stereo_meter_channel(
        self,
        renderer,
        x: float,
        y: float,
        width: float,
        height: float,
        peak_dbfs: float,
        hold_dbfs: float,
        clipped: bool,
        channel: str,
    ) -> None:
        label_width, _ = renderer.text_measure(channel, scale=0.72)
        renderer.text(
            channel,
            x - label_width - 5.0,
            y + height + 1.0,
            scale=0.72,
        )

        renderer.rect(
            x, y, width, height,
            color=(0.08, 0.09, 0.10, 0.92),
            origin=(0.0, 0.0),
            radius=1.5,
        )

        fill_width = width * self._dbfs_to_meter(peak_dbfs)
        if fill_width > 0.0:
            green_end = width * self._dbfs_to_meter(-12.0)
            yellow_end = width * self._dbfs_to_meter(-3.0)

            green_width = min(fill_width, green_end)
            if green_width > 0.0:
                renderer.rect(
                    x, y, green_width, height,
                    color=(0.18, 0.82, 0.28, 1.0),
                    origin=(0.0, 0.0), radius=1.5,
                )

            yellow_width = max(0.0, min(fill_width, yellow_end) - green_end)
            if yellow_width > 0.0:
                renderer.rect(
                    x + green_end, y, yellow_width, height,
                    color=(0.92, 0.78, 0.16, 1.0),
                    origin=(0.0, 0.0),
                )

            red_width = max(0.0, fill_width - yellow_end)
            if red_width > 0.0:
                renderer.rect(
                    x + yellow_end, y, red_width, height,
                    color=(0.95, 0.24, 0.18, 1.0),
                    origin=(0.0, 0.0), radius=1.5,
                )

        hold = self._dbfs_to_meter(hold_dbfs)
        if hold > 0.0:
            hold_x = x + min(width - 1.0, width * hold)
            renderer.rect(
                hold_x, y, 1.5, height,
                color=(1.0, 1.0, 1.0, 0.95),
                origin=(0.0, 0.0),
            )

        if clipped:
            renderer.rect(
                x + width + 3.0, y, 4.0, height,
                color=(1.0, 0.12, 0.08, 1.0),
                origin=(0.0, 0.0), radius=1.0,
            )

    @staticmethod
    def _dbfs_to_meter(
        value: float,
        floor_db: float = -60.0,
    ) -> float:
        if value == float("-inf"):
            return 0.0
        if value <= floor_db:
            return 0.0
        if value >= 0.0:
            return 1.0
        return (value - floor_db) / (-floor_db)

    # ==========================================================
    # RIGHT SIDE
    # ==========================================================

    def _build_right_lines(
        self,
        renderer,
    ) -> list[str]:
        data = (
            self.metrics.snapshot
        )

        context = (
            self.engine.gpu_context
        )

        # ------------------------------------------------------
        # Python / GIL
        # ------------------------------------------------------

        gil_function = getattr(
            sys,
            "_is_gil_enabled",
            None,
        )

        if gil_function is None:
            gil_enabled = True

        else:
            try:
                gil_enabled = bool(
                    gil_function()
                )

            except Exception:
                gil_enabled = True

        free_threaded = bool(
            sysconfig.get_config_var(
                "Py_GIL_DISABLED"
            )
        )

        python_mode = (
            "free-threaded"
            if free_threaded
            else "standard"
        )

        gil_text = (
            "enabled"
            if gil_enabled
            else "disabled"
        )

        # ------------------------------------------------------
        # Window
        # ------------------------------------------------------

        window_mode = getattr(
            context.window_mode,
            "value",
            str(
                context.window_mode
            ),
        )

        vsync = (
            "on"
            if context.vsync
            else "off"
        )

        # ------------------------------------------------------
        # GPU device
        # ------------------------------------------------------

        gpu_device = (
            data.gpu_device_name
            if data.gpu_device_name
            else "N/A"
        )

        # ------------------------------------------------------
        # Process GPU load
        # ------------------------------------------------------

        if (
            data.gpu_process_load_percent
            is None
        ):
            gpu_load = "N/A"

        else:
            gpu_load = (
                f"{data.gpu_process_load_percent:.1f} %"
            )

        # ------------------------------------------------------
        # Process GPU memory
        # ------------------------------------------------------

        if (
            data.gpu_process_memory_mb
            is None
        ):
            gpu_memory = "N/A"

        elif (
            data.gpu_process_memory_mb
            >= 1024.0
        ):
            gpu_memory = (
                f"{data.gpu_process_memory_mb / 1024.0:.2f} GB"
            )

        else:
            gpu_memory = (
                f"{data.gpu_process_memory_mb:.0f} MB"
            )

        # ------------------------------------------------------
        # Output
        # ------------------------------------------------------

        return [
            "Renderer",
            "------------------------",

            (
                "Python: "
                f"{platform.python_version()} "
                f"{python_mode}"
            ),

            (
                "GIL: "
                f"{gil_text}"
            ),

            (
                "Time scale: "
                f"{self.engine.time.time_scale:.2f}"
            ),

            "",

            (
                "Resolution: "
                f"{renderer.width}x"
                f"{renderer.height}"
            ),

            (
                "GPU Backend: "
                f"{context.driver}"
            ),

            (
                "GPU Device: "
                f"{gpu_device}"
            ),

            (
                "VSync: "
                f"{vsync}"
            ),

            (
                "Window: "
                f"{window_mode}"
            ),

            "",

            (
                "Game GPU Load: "
                f"{gpu_load}"
            ),

            (
                "Game GPU VRAM: "
                f"{gpu_memory}"
            ),
        ]

    # ==========================================================
    # TEXT LAYOUT
    # ==========================================================

    def _line_height(
        self,
        renderer,
    ) -> float:
        _, height = (
            renderer.text_measure(
                "Ag",
                scale=self.text_scale,
            )
        )

        return (
            height
            + self.line_spacing
        )

    # ==========================================================
    # LEFT DRAW
    # ==========================================================

    def _draw_left(
        self,
        renderer,
        lines: list[str],
    ) -> None:
        half_width = (
            renderer.width
            * 0.5
        )

        half_height = (
            renderer.height
            * 0.5
        )

        x = (
            -half_width
            + self.margin
        )

        y = (
            -half_height
            + self.margin
            + renderer.text_baseline(
                scale=self.text_scale
            )
        )

        line_height = (
            self._line_height(
                renderer
            )
        )

        for line in lines:
            if line:
                renderer.text(
                    line,
                    x,
                    y,
                    scale=self.text_scale,
                )

            y += (
                line_height
            )

    # ==========================================================
    # RIGHT DRAW
    # ==========================================================

    def _draw_right(
        self,
        renderer,
        lines: list[str],
    ) -> None:
        half_width = (
            renderer.width
            * 0.5
        )

        half_height = (
            renderer.height
            * 0.5
        )

        right = (
            half_width
            - self.margin
        )

        y = (
            -half_height
            + self.margin
            + renderer.text_baseline(
                scale=self.text_scale
            )
        )

        line_height = (
            self._line_height(
                renderer
            )
        )

        for line in lines:
            if line:
                width, _ = (
                    renderer.text_measure(
                        line,
                        scale=self.text_scale,
                    )
                )

                renderer.text(
                    line,
                    right - width,
                    y,
                    scale=self.text_scale,
                )

            y += (
                line_height
            )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        self.metrics.shutdown()