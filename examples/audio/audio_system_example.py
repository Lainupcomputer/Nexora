from __future__ import annotations

from nexora import Game

from nexora.audio import (
    AudioChannel,
    AudioSource,
    RepeatMode,
)


class AudioSystemExample(Game):
    """
    Comprehensive Nexora audio system example.

    This example demonstrates:

        - sound loading
        - AudioSource playback
        - pause / resume / stop
        - looping
        - volume
        - pitch
        - seeking
        - fade in / fade out
        - 2D spatial audio
        - listener movement
        - channel volume
        - audio bus volume
        - audio bus mute
        - master volume
        - MusicPlayer
        - music queue
        - previous / next
        - shuffle
        - repeat modes

    Assets
    ------
    Uses:

        assets/demo_sound.wav

    The same sound is also used for the music queue so the
    MusicPlayer API can be demonstrated without requiring
    additional assets.
    """

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title="Nexora - Audio System Example",
            width=1280,
            height=720,
            target_fps=144,
            resizable=True,
        )

        self.sound = None

        self.source: AudioSource | None = None
        self.spatial_source: AudioSource | None = None

        # ------------------------------------------------------
        # Demo values
        # ------------------------------------------------------

        self.source_volume = 1.0
        self.pitch = 1.0

        self.master_volume = 1.0
        self.sfx_volume = 1.0
        self.sfx_bus_volume = 1.0

        # ------------------------------------------------------
        # Spatial audio
        # ------------------------------------------------------

        self.listener_x = 0.0
        self.listener_y = 0.0

        self.spatial_x = 300.0
        self.spatial_y = 0.0

        self.spatial_speed = 250.0

    # ==========================================================
    # INITIALIZE
    # ==========================================================

    def initialize(
        self,
    ) -> None:
        # ======================================================
        # INPUT
        # ======================================================

        # ------------------------------------------------------
        # Basic playback
        # ------------------------------------------------------

        self.input.bind(
            "play",
            "1",
        )

        self.input.bind(
            "pause",
            "2",
        )

        self.input.bind(
            "resume",
            "3",
        )

        self.input.bind(
            "stop",
            "4",
        )

        self.input.bind(
            "loop",
            "5",
        )

        # ------------------------------------------------------
        # Volume
        # ------------------------------------------------------

        self.input.bind(
            "volume_down",
            "Q",
        )

        self.input.bind(
            "volume_up",
            "E",
        )

        # ------------------------------------------------------
        # Pitch
        # ------------------------------------------------------

        self.input.bind(
            "pitch_down",
            "Z",
        )

        self.input.bind(
            "pitch_up",
            "X",
        )

        self.input.bind(
            "pitch_reset",
            "C",
        )

        # ------------------------------------------------------
        # Seek
        # ------------------------------------------------------

        self.input.bind(
            "seek_start",
            "HOME",
        )

        self.input.bind(
            "seek_middle",
            "END",
        )

        # ------------------------------------------------------
        # Fade
        # ------------------------------------------------------

        self.input.bind(
            "fade_in",
            "F",
        )

        self.input.bind(
            "fade_out",
            "G",
        )

        # ------------------------------------------------------
        # Spatial source
        # ------------------------------------------------------

        self.input.bind(
            "spatial_play",
            "P",
        )

        self.input.bind(
            "spatial_left",
            "LEFT",
        )

        self.input.bind(
            "spatial_right",
            "RIGHT",
        )

        self.input.bind(
            "spatial_up",
            "UP",
        )

        self.input.bind(
            "spatial_down",
            "DOWN",
        )

        self.input.bind(
            "listener_left",
            "A",
        )

        self.input.bind(
            "listener_right",
            "D",
        )

        self.input.bind(
            "listener_up",
            "W",
        )

        self.input.bind(
            "listener_down",
            "S",
        )

        # ------------------------------------------------------
        # SFX bus
        # ------------------------------------------------------

        self.input.bind(
            "bus_down",
            "J",
        )

        self.input.bind(
            "bus_up",
            "K",
        )

        self.input.bind(
            "bus_mute",
            "M",
        )

        # ------------------------------------------------------
        # Master
        # ------------------------------------------------------

        self.input.bind(
            "master_down",
            "N",
        )

        self.input.bind(
            "master_up",
            "B",
        )

        # ------------------------------------------------------
        # Music player
        # ------------------------------------------------------

        self.input.bind(
            "music_play",
            "F1",
        )

        self.input.bind(
            "music_pause",
            "F2",
        )

        self.input.bind(
            "music_resume",
            "F3",
        )

        self.input.bind(
            "music_stop",
            "F4",
        )

        self.input.bind(
            "music_next",
            "F5",
        )

        self.input.bind(
            "music_previous",
            "F6",
        )

        self.input.bind(
            "music_shuffle",
            "F7",
        )

        self.input.bind(
            "music_repeat",
            "F8",
        )

        # ------------------------------------------------------
        # Exit
        # ------------------------------------------------------

        self.input.bind(
            "escape",
            "ESCAPE",
        )

        # ======================================================
        # LOAD SOUND
        # ======================================================

        print(
            r"Loading: assets\demo_sound.wav"
        )

        self.sound = self.audio.load(
            "assets/demo_sound.wav"
        )

        print()
        print(
            f"Duration: "
            f"{self.sound.duration:.2f}s"
        )

        print(
            f"Frequency: "
            f"{self.sound.frequency} Hz"
        )

        print(
            f"Channels: "
            f"{self.sound.channels}"
        )

        print(
            f"Size: "
            f"{self.sound.size} bytes"
        )

        # ======================================================
        # NORMAL SFX SOURCE
        # ======================================================

        self.source = AudioSource(
            self.sound,

            channel=AudioChannel.SFX,

            volume=1.0,

            loop=False,

            pitch=1.0,

            bus=self.audio.get_bus(
                "SFX"
            ),
        )

        # ======================================================
        # SPATIAL SOURCE
        # ======================================================

        self.spatial_source = AudioSource(
            self.sound,

            channel=AudioChannel.SFX,

            volume=1.0,

            loop=True,

            position=(
                self.spatial_x,
                self.spatial_y,
            ),

            min_distance=50.0,
            max_distance=800.0,

            bus=self.audio.get_bus(
                "SFX"
            ),
        )

        # ======================================================
        # LISTENER
        # ======================================================

        self.audio.player.listener.set_position(
            self.listener_x,
            self.listener_y,
        )

        # ======================================================
        # MUSIC DEMO QUEUE
        # ======================================================
        #
        # We only have one demo WAV, so it is queued multiple
        # times to demonstrate the queue system.
        # ======================================================

        self.audio.music.enqueue(
            self.sound
        )

        self.audio.music.enqueue(
            self.sound
        )

        self.audio.music.enqueue(
            self.sound
        )

        # ======================================================
        # INFO
        # ======================================================

        self._print_controls()

    # ==========================================================
    # CONTROLS
    # ==========================================================

    @staticmethod
    def _print_controls() -> None:
        print()
        print("=" * 72)
        print(" Nexora Audio System Example")
        print("=" * 72)
        print()

        print("BASIC SOURCE")
        print("-" * 72)

        print("1        Play")
        print("2        Pause")
        print("3        Resume")
        print("4        Stop")
        print("5        Toggle loop")

        print()
        print("SOURCE VOLUME")
        print("-" * 72)

        print("Q        Volume -")
        print("E        Volume +")

        print()
        print("PITCH")
        print("-" * 72)

        print("Z        Pitch -")
        print("X        Pitch +")
        print("C        Pitch reset")

        print()
        print("SEEK")
        print("-" * 72)

        print("HOME     Seek to start")
        print("END      Seek to middle")

        print()
        print("FADES")
        print("-" * 72)

        print("F        Fade in")
        print("G        Fade out")

        print()
        print("SPATIAL AUDIO")
        print("-" * 72)

        print("P        Play spatial looping source")

        print("Arrows   Move sound source")
        print("WASD     Move listener")

        print()
        print("SFX BUS")
        print("-" * 72)

        print("J        SFX bus volume -")
        print("K        SFX bus volume +")
        print("M        Toggle SFX bus mute")

        print()
        print("MASTER")
        print("-" * 72)

        print("N        Master volume -")
        print("B        Master volume +")

        print()
        print("MUSIC")
        print("-" * 72)

        print("F1       Music play")
        print("F2       Music pause")
        print("F3       Music resume")
        print("F4       Music stop")
        print("F5       Next track")
        print("F6       Previous track")
        print("F7       Toggle shuffle")
        print("F8       Change repeat mode")

        print()
        print("ESC      Exit")
        print()

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        # ======================================================
        # EXIT
        # ======================================================

        if self.input.action(
            "escape"
        ).pressed:
            self.stop()
            return

        source = self.source
        spatial = self.spatial_source

        # ======================================================
        # BASIC PLAYBACK
        # ======================================================

        if source is not None:
            if self.input.action(
                "play"
            ).pressed:
                self.audio.player.play(
                    source
                )

                print(
                    "[SFX] Play"
                )

            if self.input.action(
                "pause"
            ).pressed:
                self.audio.player.pause(
                    source
                )

                print(
                    "[SFX] Pause"
                )

            if self.input.action(
                "resume"
            ).pressed:
                self.audio.player.resume(
                    source
                )

                print(
                    "[SFX] Resume"
                )

            if self.input.action(
                "stop"
            ).pressed:
                self.audio.player.stop(
                    source
                )

                print(
                    "[SFX] Stop"
                )

            # ==================================================
            # LOOP
            # ==================================================

            if self.input.action(
                "loop"
            ).pressed:
                source.loop = (
                    not source.loop
                )

                print(
                    f"[SFX] Loop: "
                    f"{source.loop}"
                )

            # ==================================================
            # SOURCE VOLUME
            # ==================================================

            if self.input.action(
                "volume_down"
            ).pressed:
                self.source_volume = max(
                    0.0,
                    self.source_volume
                    - 0.1,
                )

                source.volume = (
                    self.source_volume
                )

                print(
                    f"[SFX] Volume: "
                    f"{source.volume:.2f}"
                )

            if self.input.action(
                "volume_up"
            ).pressed:
                self.source_volume = min(
                    1.0,
                    self.source_volume
                    + 0.1,
                )

                source.volume = (
                    self.source_volume
                )

                print(
                    f"[SFX] Volume: "
                    f"{source.volume:.2f}"
                )

            # ==================================================
            # PITCH
            # ==================================================

            if self.input.action(
                "pitch_down"
            ).pressed:
                self.pitch = max(
                    0.25,
                    self.pitch
                    - 0.1,
                )

                source.pitch = (
                    self.pitch
                )

                print(
                    f"[SFX] Pitch: "
                    f"{source.pitch:.2f}"
                )

            if self.input.action(
                "pitch_up"
            ).pressed:
                self.pitch = min(
                    3.0,
                    self.pitch
                    + 0.1,
                )

                source.pitch = (
                    self.pitch
                )

                print(
                    f"[SFX] Pitch: "
                    f"{source.pitch:.2f}"
                )

            if self.input.action(
                "pitch_reset"
            ).pressed:
                self.pitch = 1.0

                source.pitch = 1.0

                print(
                    "[SFX] Pitch reset"
                )

            # ==================================================
            # SEEK
            # ==================================================

            if self.input.action(
                "seek_start"
            ).pressed:
                source.seek_seconds(
                    0.0
                )

                print(
                    "[SFX] Seek: 0.00s"
                )

            if self.input.action(
                "seek_middle"
            ).pressed:
                target = (
                    source.duration
                    * 0.5
                )

                source.seek_seconds(
                    target
                )

                print(
                    f"[SFX] Seek: "
                    f"{target:.2f}s"
                )

            # ==================================================
            # FADE
            # ==================================================

            if self.input.action(
                "fade_in"
            ).pressed:
                source.play()

                source.fade_in(
                    2.0
                )

                print(
                    "[SFX] Fade in: 2.0s"
                )

            if self.input.action(
                "fade_out"
            ).pressed:
                source.fade_out(
                    2.0
                )

                print(
                    "[SFX] Fade out: 2.0s"
                )

        # ======================================================
        # SPATIAL AUDIO PLAYBACK
        # ======================================================

        if (
            spatial is not None
            and self.input.action(
                "spatial_play"
            ).pressed
        ):
            if spatial.playing:
                spatial.stop()

                print(
                    "[Spatial] Stop"
                )

            else:
                self.audio.player.play(
                    spatial
                )

                print(
                    "[Spatial] Play"
                )

        # ======================================================
        # MOVE SPATIAL SOURCE
        # ======================================================

        if spatial is not None:
            move_amount = (
                self.spatial_speed
                * delta_time
            )

            if self.input.action(
                "spatial_left"
            ).down:
                self.spatial_x -= (
                    move_amount
                )

            if self.input.action(
                "spatial_right"
            ).down:
                self.spatial_x += (
                    move_amount
                )

            if self.input.action(
                "spatial_up"
            ).down:
                self.spatial_y -= (
                    move_amount
                )

            if self.input.action(
                "spatial_down"
            ).down:
                self.spatial_y += (
                    move_amount
                )

            spatial.position_2d = (
                self.spatial_x,
                self.spatial_y,
            )

        # ======================================================
        # MOVE LISTENER
        # ======================================================

        listener_move = (
            self.spatial_speed
            * delta_time
        )

        if self.input.action(
            "listener_left"
        ).down:
            self.listener_x -= (
                listener_move
            )

        if self.input.action(
            "listener_right"
        ).down:
            self.listener_x += (
                listener_move
            )

        if self.input.action(
            "listener_up"
        ).down:
            self.listener_y -= (
                listener_move
            )

        if self.input.action(
            "listener_down"
        ).down:
            self.listener_y += (
                listener_move
            )

        self.audio.player.listener.set_position(
            self.listener_x,
            self.listener_y,
        )

        # ======================================================
        # SFX BUS
        # ======================================================

        sfx_bus = (
            self.audio.get_bus(
                "SFX"
            )
        )

        if self.input.action(
            "bus_down"
        ).pressed:
            self.sfx_bus_volume = max(
                0.0,
                self.sfx_bus_volume
                - 0.1,
            )

            sfx_bus.volume = (
                self.sfx_bus_volume
            )

            print(
                f"[Bus:SFX] Volume: "
                f"{sfx_bus.volume:.2f}"
            )

        if self.input.action(
            "bus_up"
        ).pressed:
            self.sfx_bus_volume = min(
                1.0,
                self.sfx_bus_volume
                + 0.1,
            )

            sfx_bus.volume = (
                self.sfx_bus_volume
            )

            print(
                f"[Bus:SFX] Volume: "
                f"{sfx_bus.volume:.2f}"
            )

        if self.input.action(
            "bus_mute"
        ).pressed:
            sfx_bus.toggle_mute()

            print(
                f"[Bus:SFX] Muted: "
                f"{sfx_bus.muted}"
            )

        # ======================================================
        # MASTER CHANNEL
        # ======================================================

        if self.input.action(
            "master_down"
        ).pressed:
            self.master_volume = max(
                0.0,
                self.master_volume
                - 0.1,
            )

            self.audio.set_volume(
                AudioChannel.MASTER,
                self.master_volume,
            )

            print(
                f"[Master] Volume: "
                f"{self.master_volume:.2f}"
            )

        if self.input.action(
            "master_up"
        ).pressed:
            self.master_volume = min(
                1.0,
                self.master_volume
                + 0.1,
            )

            self.audio.set_volume(
                AudioChannel.MASTER,
                self.master_volume,
            )

            print(
                f"[Master] Volume: "
                f"{self.master_volume:.2f}"
            )

        # ======================================================
        # MUSIC PLAYER
        # ======================================================

        music = (
            self.audio.music
        )

        if self.input.action(
            "music_play"
        ).pressed:
            if self.sound is not None:
                music.play(
                    self.sound
                )

                print(
                    "[Music] Play"
                )

        if self.input.action(
            "music_pause"
        ).pressed:
            music.pause()

            print(
                "[Music] Pause"
            )

        if self.input.action(
            "music_resume"
        ).pressed:
            music.resume()

            print(
                "[Music] Resume"
            )

        if self.input.action(
            "music_stop"
        ).pressed:
            music.stop()

            print(
                "[Music] Stop"
            )

        if self.input.action(
            "music_next"
        ).pressed:
            result = (
                music.play_next()
            )

            print(
                f"[Music] Next: "
                f"{result}"
            )

        if self.input.action(
            "music_previous"
        ).pressed:
            result = (
                music.previous()
            )

            print(
                f"[Music] Previous: "
                f"{result}"
            )

        # ======================================================
        # SHUFFLE
        # ======================================================

        if self.input.action(
            "music_shuffle"
        ).pressed:
            music.set_shuffle(
                not music.shuffle
            )

            print(
                f"[Music] Shuffle: "
                f"{music.shuffle}"
            )

        # ======================================================
        # REPEAT MODE
        # ======================================================

        if self.input.action(
            "music_repeat"
        ).pressed:
            if (
                music.repeat
                == RepeatMode.OFF
            ):
                mode = (
                    RepeatMode.ONE
                )

            elif (
                music.repeat
                == RepeatMode.ONE
            ):
                mode = (
                    RepeatMode.ALL
                )

            else:
                mode = (
                    RepeatMode.OFF
                )

            music.set_repeat(
                mode
            )

            print(
                f"[Music] Repeat: "
                f"{music.repeat.value}"
            )

        # ======================================================
        # MUSIC QUEUE UPDATE
        # ======================================================
        #
        # AudioPlayer.update() is already called by GameLoop.
        #
        # MusicPlayer.update() handles:
        #
        #     track ended
        #     next queue item
        #     repeat
        #
        # ======================================================

        music.update()

    # ==========================================================
    # RENDER
    # ==========================================================

    def render(
        self,
        interpolation: float,
    ) -> None:
        # Audio example intentionally has no graphics.
        pass

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
    ) -> None:
        # ------------------------------------------------------
        # Stop sources
        # ------------------------------------------------------

        if self.source is not None:
            self.source.stop()

            self.source = None

        if self.spatial_source is not None:
            self.spatial_source.stop()

            self.spatial_source = None

        # ------------------------------------------------------
        # Stop music
        # ------------------------------------------------------

        self.audio.music.stop()

        # ------------------------------------------------------
        # Clear queue/history
        # ------------------------------------------------------

        self.audio.music.clear_queue()
        self.audio.music.clear_history()

        # ------------------------------------------------------
        # Base game shutdown
        # ------------------------------------------------------

        super().shutdown()


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    AudioSystemExample().run()