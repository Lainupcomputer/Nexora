from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import textwrap


PROJECT_NAME_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_-]*"
)

NEXORA_ENGINE_REQUIREMENT = (
    "nexora-engine>=0.1.0"
)


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    """Description of a project created by the generator."""

    root: Path
    directories: tuple[Path, ...]
    files: tuple[Path, ...]


def _valid_project_name(name: str) -> bool:
    """Return whether *name* is safe for a generated project folder."""

    return bool(
        isinstance(name, str)
        and PROJECT_NAME_PATTERN.fullmatch(name)
    )


def project_class_name(name: str) -> str:
    """Convert a CLI project name into a valid Python class name.

    Examples
    --------
    ``MyGame`` -> ``MyGame``
    ``my-game`` -> ``MyGame``
    ``my_game`` -> ``MyGame``
    """

    normalized = str(name).strip()

    if not _valid_project_name(normalized):
        raise ValueError(
            f"Invalid project name: {name!r}."
        )

    parts = (
        part
        for part in re.split(r"[-_]+", normalized)
        if part
    )

    class_name = "".join(
        part[:1].upper() + part[1:]
        for part in parts
    )

    if not class_name:
        raise ValueError(
            f"Could not derive a Python class name from {name!r}."
        )

    return class_name


def _normalize_project_name(name: str) -> str:
    normalized = str(name).strip()

    if not _valid_project_name(normalized):
        raise ValueError(
            f"Invalid project name: {name!r}. "
            "Project names must start with a letter or underscore "
            "and may contain only letters, numbers, '-' and '_'."
        )

    return normalized


def _display_name(name: str) -> str:
    """Return a readable window title without changing camel case names."""

    if "-" not in name and "_" not in name:
        return name

    return re.sub(
        r"[-_]+",
        " ",
        name,
    ).strip().title()


def _clean_template(template: str) -> str:
    return textwrap.dedent(template).lstrip()


def _main_template(class_name: str) -> str:
    return _clean_template(
        f"""\
        from __future__ import annotations

        from game import {class_name}


        def main() -> None:
            game = {class_name}()
            game.run()


        if __name__ == "__main__":
            main()
        """
    )


def _game_template(
    project_name: str,
    title: str,
    class_name: str,
) -> str:
    return _clean_template(
        f"""\
        from __future__ import annotations

        from nexora import Game
        from scenes import MainScene


        class {class_name}(Game):
            \"\"\"Minimal game created by ``nexora create``.\"\"\"

            def __init__(self) -> None:
                super().__init__(
                    project_name={project_name!r},
                    title={title!r},
                    width=1280,
                    height=720,
                    resizable=True,
                    target_fps=144,
                )

            def initialize(self) -> None:
                self.scene = MainScene(self)
        """
    )


def _scene_template() -> str:
    return _clean_template(
        """\
        from __future__ import annotations

        from nexora.scene import Scene


        class MainScene(Scene):
            \"\"\"Initial scene for a generated Nexora game.\"\"\"

            def __init__(self, game) -> None:
                super().__init__(\"Main\")
                self.game = game

            def update(self, delta_time: float) -> None:
                super().update(delta_time)

                # The default Nexora binding maps Escape to ``pause``.
                if (
                    self.game.input is not None
                    and self.game.input.action_pressed.pause
                ):
                    self.game.stop()

            def render(self, interpolation: float) -> None:
                if self.game.renderer is None:
                    return

                # World coordinates use the renderer's centered origin.
                self.game.renderer.rect(
                    -160.0,
                    -90.0,
                    320.0,
                    180.0,
                    color=(0.24, 0.12, 0.34, 1.0),
                    radius=12.0,
                )
        """
    )


def _scenes_init_template() -> str:
    return _clean_template(
        """\
        from scenes.main_scene import MainScene

        __all__ = [\"MainScene\"]
        """
    )


def _pyproject_template(
    project_name: str,
    title: str,
) -> str:
    description = (
        f"A game built with Nexora Engine - {title}."
    )

    return _clean_template(
        f"""\
        [build-system]
        requires = [\"setuptools>=75\"]
        build-backend = \"setuptools.build_meta\"


        [project]
        name = {project_name!r}
        version = \"0.1.0\"
        description = {description!r}
        requires-python = \">=3.13\"
        dependencies = [
            {NEXORA_ENGINE_REQUIREMENT!r},
        ]


        [project.optional-dependencies]
        dev = [\"pytest>=9.0\"]


        [tool.setuptools]
        py-modules = [\"game\", \"main\"]


        [tool.setuptools.packages.find]
        include = [\"scenes*\"]


        [tool.pytest.ini_options]
        testpaths = [\"tests\"]
        """
    )


def _readme_template(
    project_name: str,
    title: str,
) -> str:
    return _clean_template(
        f"""\
        # {project_name}

        A starter game generated with Nexora Engine.

        ## Start the game

        Nexora must be installed in the Python environment first. From a
        Nexora source checkout, install the engine with `pip install -e .`.

        Run the generated project from its root directory:

        ```powershell
        python -Xgil=0 main.py
        ```

        Press **Escape** to close the window.

        ## Open the editor

        ```powershell
        python -m nexora --editor .
        ```

        ## Install this project

        ```powershell
        python -m pip install -e \".[dev]\"
        python -Xgil=0 -m pytest
        ```

        ## Project structure

        ```text
        {project_name}/
        ├── assets/
        │   ├── audio/
        │   ├── fonts/
        │   ├── sprites/
        │   └── textures/
        ├── scenes/
        │   ├── __init__.py
        │   └── main_scene.py
        ├── scripts/
        ├── tests/
        │   └── test_game.py
        ├── game.py
        ├── main.py
        ├── pyproject.toml
        └── README.md
        ```

        The initial window title is **{title}**. Extend `game.py` and
        `scenes/main_scene.py` as the game grows.
        """
    )


GITIGNORE_TEMPLATE = _clean_template(
    """\
    __pycache__/
    *.py[cod]
    *.egg-info/
    .venv/
    .pytest_cache/
    build/
    dist/
    """
)


def _test_template(
    project_name: str,
    title: str,
    class_name: str,
) -> str:
    return _clean_template(
        f"""\
        from game import {class_name}


        def test_generated_game_metadata() -> None:
            game = {class_name}()

            assert game.project_name == {project_name!r}
            assert game.title == {title!r}
        """
    )


def _project_contents(
    root: Path,
    *,
    project_name: str,
    title: str,
    class_name: str,
) -> tuple[tuple[Path, ...], dict[Path, str]]:
    directories = (
        root / "assets",
        root / "assets" / "audio",
        root / "assets" / "fonts",
        root / "assets" / "sprites",
        root / "assets" / "textures",
        root / "scenes",
        root / "scripts",
        root / "tests",
    )

    files = {
        root / "main.py": _main_template(class_name),
        root / "game.py": _game_template(
            project_name,
            title,
            class_name,
        ),
        root / "scenes" / "__init__.py": _scenes_init_template(),
        root / "scenes" / "main_scene.py": _scene_template(),
        root / "pyproject.toml": _pyproject_template(
            project_name,
            title,
        ),
        root / "README.md": _readme_template(
            project_name,
            title,
        ),
        root / ".gitignore": GITIGNORE_TEMPLATE,
        root / "tests" / "test_game.py": _test_template(
            project_name,
            title,
            class_name,
        ),
    }

    for directory in directories:
        if directory.name in {
            "audio",
            "fonts",
            "sprites",
            "textures",
        }:
            files[directory / ".gitkeep"] = ""

    files[root / "scripts" / ".gitkeep"] = ""

    return directories, files


def generate_project(
    name: str,
    path: str | Path = ".",
) -> GeneratedProject:
    """Create a complete Nexora starter project.

    The destination must not already contain a directory with the requested
    project name. Existing projects are never modified.
    """

    project_name = _normalize_project_name(name)
    class_name = project_class_name(project_name)
    parent = Path(path).expanduser().resolve()

    if parent.exists() and not parent.is_dir():
        raise NotADirectoryError(
            f"Project destination is not a directory: {parent}"
        )

    parent.mkdir(parents=True, exist_ok=True)

    root = parent / project_name

    if root.exists():
        raise FileExistsError(
            f"Project already exists: {root}"
        )

    root.mkdir()

    directories, files = _project_contents(
        root,
        project_name=project_name,
        title=_display_name(project_name),
        class_name=class_name,
    )

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    for file_path, content in files.items():
        file_path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )

    return GeneratedProject(
        root=root,
        directories=directories,
        files=tuple(files),
    )


def create_project(
    name: str,
    path: str | Path = ".",
) -> int:
    """CLI-facing wrapper around :func:`generate_project`."""

    try:
        project = generate_project(
            name=name,
            path=path,
        )

    except (
        ValueError,
        FileExistsError,
        NotADirectoryError,
        OSError,
    ) as exc:
        print(f"Error: {exc}")
        return 1

    print()
    print("=" * 48)
    print(" Nexora Engine - Create Project")
    print("=" * 48)
    print()
    print(f"Created project: {project.root}")
    print()

    for directory in project.directories:
        print(
            f"✓ Created {directory.relative_to(project.root)}"
        )

    for file_path in project.files:
        print(
            f"✓ Created {file_path.relative_to(project.root)}"
        )

    print()
    print("Project created successfully!")
    print()
    print("Next steps:")
    print(f"  cd {project.root.name}")
    print("  python -Xgil=0 main.py")
    print("  python -m nexora --editor .")
    print()

    return 0
