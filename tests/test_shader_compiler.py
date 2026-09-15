from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from nexora.rendering.shaders import ShaderCompiler


def test_output_name() -> None:
    assert (
        ShaderCompiler.output_name(Path("sprite.vert.hlsl"))
        == "sprite.vert.spv"
    )


def test_needs_build_when_output_missing(tmp_path: Path) -> None:
    source = tmp_path / "sprite.vert.hlsl"
    output = tmp_path / "bin" / "sprite.vert.spv"
    source.write_text("shader", encoding="utf-8")

    compiler = ShaderCompiler(
        source_dir=tmp_path,
        output_dir=tmp_path / "bin",
        dxc_path=tmp_path / "dxc.exe",
    )

    assert compiler.needs_build(source, output)


def test_compile_all_writes_directly_to_project_bin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "engine_shaders"
    output_dir = tmp_path / "Documents" / "MyGame" / "shaders" / "bin"
    source_dir.mkdir()

    source = source_dir / "sprite.vert.hlsl"
    source.write_text("shader", encoding="utf-8")

    dxc = tmp_path / "dxc.exe"
    dxc.write_bytes(b"fake")

    def fake_run(command, **kwargs):
        output = Path(command[command.index("-Fo") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"spirv")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nexora.rendering.shaders.compiler.subprocess.run",
        fake_run,
    )

    compiler = ShaderCompiler(
        source_dir=source_dir,
        output_dir=output_dir,
        dxc_path=dxc,
    )

    result = compiler.compile_all()

    assert result.built_count == 1
    assert result.skipped_count == 0
    assert (output_dir / "sprite.vert.spv").read_bytes() == b"spirv"

    # The compiler never creates an intermediate engine/bin directory.
    assert not (source_dir / "bin").exists()


def test_compile_all_skips_current_shader(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "shaders"
    output_dir = tmp_path / "runtime"
    source_dir.mkdir()
    output_dir.mkdir()

    source = source_dir / "sprite.frag.hlsl"
    output = output_dir / "sprite.frag.spv"
    source.write_text("shader", encoding="utf-8")
    output.write_bytes(b"spirv")

    # Make output strictly newer than source.
    source.touch()
    output.touch()

    dxc = tmp_path / "dxc.exe"
    dxc.write_bytes(b"fake")

    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("DXC should not run for an up-to-date shader")

    monkeypatch.setattr(
        "nexora.rendering.shaders.compiler.subprocess.run",
        fake_run,
    )

    compiler = ShaderCompiler(
        source_dir=source_dir,
        output_dir=output_dir,
        dxc_path=dxc,
    )

    result = compiler.compile_all()

    assert result.built_count == 0
    assert result.skipped_count == 1
    assert not called
