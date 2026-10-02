from types import SimpleNamespace

from nexora.debug.overlay import DebugOverlay


def _bus(name, *, parent=None, peak=(-12.0, -10.0), volume=1.0, pan=0.0,
         muted=False, solo=False, clipped=False, effects=()):
    return SimpleNamespace(
        id=name.lower(),
        name=name,
        parent=parent,
        peak_dbfs=peak,
        volume=volume,
        pan=pan,
        muted=muted,
        solo=solo,
        clipped=clipped,
        effects=effects,
        peak_hold_dbfs=peak,
    )


def test_debug_overlay_builds_compact_audio_mixer_lines():
    master = _bus("Master", peak=(-3.0, -2.0))
    sfx = _bus(
        "SFX",
        parent=master,
        peak=(-8.0, -7.5),
        volume=0.8,
        pan=-0.25,
        muted=True,
        effects=(object(), object()),
    )
    weapons = _bus(
        "Weapons",
        parent=sfx,
        peak=(-6.0, -5.0),
        solo=True,
        clipped=True,
    )

    sends = (
        SimpleNamespace(source_bus_id=sfx.id),
        SimpleNamespace(source_bus_id=weapons.id),
    )

    audio = SimpleNamespace(
        player=SimpleNamespace(sources=(object(), object())),
        device=SimpleNamespace(initialized=False),
        get_buses=lambda: (master, sfx, weapons),
        get_sends=lambda: sends,
    )

    overlay = object.__new__(DebugOverlay)
    overlay.engine = SimpleNamespace(audio=audio)

    lines = overlay._build_audio_mixer_lines()

    assert "Audio Mixer" in lines
    assert "Sources: 2   Buses: 3   Sends: 2" in lines
    assert any("Master:" in line and "V 1.00" in line for line in lines)
    assert any("SFX:" in line and "FX 2" in line and "Send 1" in line and "[M]" in line for line in lines)
    assert any("Weapons:" in line and "[S CLIP]" in line for line in lines)


def test_debug_overlay_limits_audio_bus_rows():
    buses = tuple(_bus(f"Bus{i}") for i in range(11))
    audio = SimpleNamespace(
        player=SimpleNamespace(sources=()),
        device=SimpleNamespace(initialized=False),
        get_buses=lambda: buses,
        get_sends=lambda: (),
    )

    overlay = object.__new__(DebugOverlay)
    overlay.engine = SimpleNamespace(audio=audio)

    lines = overlay._build_audio_mixer_lines()

    assert "... +3 buses" in lines


def test_debug_overlay_formats_silent_dbfs():
    assert DebugOverlay._format_dbfs(float("-inf")) == "-inf"
    assert DebugOverlay._format_dbfs(-120.0) == "<-99"
    assert DebugOverlay._format_dbfs(-12.34) == "-12.3"


def test_debug_overlay_dbfs_meter_mapping():
    assert DebugOverlay._dbfs_to_meter(float("-inf")) == 0.0
    assert DebugOverlay._dbfs_to_meter(-60.0) == 0.0
    assert DebugOverlay._dbfs_to_meter(-30.0) == 0.5
    assert DebugOverlay._dbfs_to_meter(0.0) == 1.0
    assert DebugOverlay._dbfs_to_meter(3.0) == 1.0


def test_debug_overlay_draws_separate_left_and_right_meter_tracks():
    master = _bus("Master", peak=(-12.0, -6.0), clipped=True)
    audio = SimpleNamespace(
        player=SimpleNamespace(sources=()),
        device=SimpleNamespace(initialized=False),
        get_buses=lambda: (master,),
        get_sends=lambda: (),
    )
    overlay = object.__new__(DebugOverlay)
    overlay.engine = SimpleNamespace(audio=audio)
    overlay.margin = 16.0
    overlay.text_scale = 1.05
    overlay.line_spacing = 5.0

    class Renderer:
        width = 1920
        height = 1080

        def __init__(self):
            self.rects = []
            self.texts = []

        def text_baseline(self, *, scale=1.0):
            return 10.0 * scale

        def text_measure(self, text, *, scale=1.0):
            return (len(text) * 7.0 * scale, 12.0 * scale)

        def rect(self, *args, **kwargs):
            self.rects.append((args, kwargs))

        def text(self, *args, **kwargs):
            self.texts.append((args, kwargs))

    renderer = Renderer()
    lines = [
        "FPS",
        "",
        "Audio Mixer",
        "------------------------",
        "Sources: 0   Buses: 1   Sends: 0",
        "Queue: N/A",
        "Master: V 1.00  P +0.00  FX 0  Send 0 [CLIP]",
    ]
    overlay._draw_audio_mixer_bottom_left(renderer, lines)

    labels = [args[0] for args, _ in renderer.texts]
    assert "L" in labels
    assert "R" in labels
    # At least two backgrounds plus level fills / hold / clip markers.
    assert len(renderer.rects) >= 6
