from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True, slots=True)
class ShaderBuildResult:
    built: tuple[Path, ...]
    skipped: tuple[Path, ...]

    @property
    def built_count(self) -> int:
        return len(self.built)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


class ShaderCompiler:
    """Incremental HLSL -> SPIR-V compiler for Nexora shaders.

    Shader sources stay with the engine package, while compiled shader
    binaries are written directly into the active project's runtime shader
    directory. There is no intermediate deployment/copy step.
    """

    _PROFILES = {
        ".vert.hlsl": "vs_6_0",
        ".frag.hlsl": "ps_6_0",
        ".comp.hlsl": "cs_6_0",
    }

    def __init__(
        self,
        *,
        source_dir: str | Path,
        output_dir: str | Path,
        dxc_path: str | Path,
    ) -> None:
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.dxc_path = Path(dxc_path)

    @staticmethod
    def _profile_for(path: Path) -> str | None:
        name = path.name.lower()
        for suffix, profile in ShaderCompiler._PROFILES.items():
            if name.endswith(suffix):
                return profile
        return None

    @staticmethod
    def output_name(source: Path) -> str:
        if not source.name.lower().endswith(".hlsl"):
            raise ValueError(f"Not an HLSL shader: {source}")
        return source.name[:-5] + ".spv"

    def needs_build(self, source: Path, output: Path) -> bool:
        if not output.is_file():
            return True
        try:
            return output.stat().st_mtime_ns < source.stat().st_mtime_ns
        except OSError:
            return True

    def compile_file(
        self,
        source: str | Path,
        *,
        force: bool = False,
    ) -> Path:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(f"Shader source not found: {source}")

        profile = self._profile_for(source)
        if profile is None:
            raise ValueError(f"Unknown shader stage: {source.name}")

        if not self.dxc_path.is_file():
            raise FileNotFoundError(
                "DXC compiler not found: "
                f"{self.dxc_path}"
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output = self.output_dir / self.output_name(source)

        if not force and not self.needs_build(source, output):
            return output

        command = [
            str(self.dxc_path),
            "-spirv",
            "-T",
            profile,
            "-E",
            "main",
            "-Fo",
            str(output),
            str(source),
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if completed.returncode != 0:
            try:
                output.unlink(missing_ok=True)
            except OSError:
                pass

            details = (completed.stderr or completed.stdout or "").strip()
            if details:
                details = f"\n{details}"

            raise RuntimeError(
                f"Shader compilation failed for {source.name} "
                f"(profile {profile}, exit {completed.returncode})."
                f"{details}"
            )

        if not output.is_file() or output.stat().st_size <= 0:
            raise RuntimeError(
                "DXC returned successfully but did not create a valid shader: "
                f"{output}"
            )

        return output

    def compile_all(self, *, force: bool = False) -> ShaderBuildResult:
        if not self.source_dir.is_dir():
            raise FileNotFoundError(
                "Nexora shader source directory does not exist: "
                f"{self.source_dir}"
            )

        sources = sorted(
            path
            for path in self.source_dir.glob("*.hlsl")
            if path.is_file() and self._profile_for(path) is not None
        )

        if not sources:
            raise FileNotFoundError(
                f"No HLSL shader sources found in: {self.source_dir}"
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)

        built: list[Path] = []
        skipped: list[Path] = []

        for source in sources:
            output = self.output_dir / self.output_name(source)
            needs_build = force or self.needs_build(source, output)
            self.compile_file(source, force=force)
            if needs_build:
                built.append(output)
            else:
                skipped.append(output)

        return ShaderBuildResult(
            built=tuple(built),
            skipped=tuple(skipped),
        )
