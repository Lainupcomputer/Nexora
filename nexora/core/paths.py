from __future__ import annotations

from pathlib import Path


# ==============================================================
# NEXORA PATHS
# ==============================================================


CORE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

NEXORA_DIR = (
    CORE_DIR.parent
)

DEFAULTS_DIR = (
    CORE_DIR
    / "defaults"
)

ENGINE_SHADER_DIR = (
    NEXORA_DIR
    / "rendering"
    / "shaders"
)

PROJECT_ROOT = NEXORA_DIR.parent

DXC_PATH = (
    PROJECT_ROOT
    / "tools"
    / "dxc"
    / "dxc.exe"
)


# ==============================================================
# PROJECT PATHS
# ==============================================================


class ProjectPaths:
    """
    Central filesystem paths for a Nexora project.

    Engine resources:

        nexora/core/defaults/
        nexora/rendering/shaders/*.hlsl

    User project data:

        Documents/<project_name>/

    Structure:

        Documents/<project_name>/
            settings/
            saves/
            shaders/
                bin/

    Engine HLSL shaders are compiled directly into:

        Documents/<project_name>/shaders/bin/

    There is no intermediate engine shader-bin copy/deploy step.
    """

    def __init__(
        self,
        project_name: str,
    ) -> None:
        project_name = str(
            project_name
        ).strip()

        if not project_name:
            raise ValueError(
                "project_name cannot be empty."
            )

        invalid = {
            "<",
            ">",
            ":",
            '"',
            "/",
            "\\",
            "|",
            "?",
            "*",
        }

        if any(
            character in project_name
            for character in invalid
        ):
            raise ValueError(
                "project_name contains invalid "
                "filesystem characters."
            )

        if project_name in {
            ".",
            "..",
        }:
            raise ValueError(
                "Invalid project_name."
            )

        self.project_name = (
            project_name
        )

        # ======================================================
        # Engine
        # ======================================================

        self.defaults = (
            DEFAULTS_DIR
        )

        self.engine_shader_dir = (
            ENGINE_SHADER_DIR
        )

        self.dxc = (
            DXC_PATH
        )

        # ======================================================
        # User
        # ======================================================

        self.documents = (
            Path.home()
            / "Documents"
        )

        self.root = (
            self.documents
            / self.project_name
        )

        # ======================================================
        # Settings
        # ======================================================

        self.settings = (
            self.root
            / "settings"
        )

        # ======================================================
        # Saves
        # ======================================================

        self.saves = (
            self.root
            / "saves"
        )

        # ======================================================
        # Shaders
        # ======================================================

        self.shaders = (
            self.root
            / "shaders"
        )

        self.shader_bin = (
            self.shaders
            / "bin"
        )

    # ==========================================================
    # CREATE
    # ==========================================================

    def ensure(
        self,
    ) -> None:
        """
        Create all writable Nexora project directories.
        """

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.settings.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.saves.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.shader_bin.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ==========================================================
    # SHADER COMPILER PATHS
    # ==========================================================

    @property
    def shader_source_dir(self) -> Path:
        """Return Nexora's HLSL source directory."""
        return self.engine_shader_dir

    @property
    def shader_compiler(self) -> Path:
        """Return the bundled DXC compiler path."""
        return self.dxc

    # ==========================================================
    # DEFAULT FILES
    # ==========================================================

    def default_file(
        self,
        file_name: str,
    ) -> Path:
        """
        Return an engine default settings file.
        """

        return (
            self.defaults
            / file_name
        )

    # ==========================================================
    # SETTINGS FILES
    # ==========================================================

    def settings_file(
        self,
        file_name: str,
    ) -> Path:
        """
        Return a project settings file.
        """

        return (
            self.settings
            / file_name
        )

    # ==========================================================
    # SAVE FILES
    # ==========================================================

    def save_file(
        self,
        file_name: str,
    ) -> Path:
        """
        Return a project save file.
        """

        return (
            self.saves
            / file_name
        )

    # ==========================================================
    # SHADER FILES
    # ==========================================================

    def shader_file(
        self,
        file_name: str,
    ) -> Path:
        """
        Return a project-local compiled shader file.

        Example:

            paths.shader_file(
                "sprite.vert.spv"
            )

        resolves to:

            Documents/<project_name>/
                shaders/bin/sprite.vert.spv
        """

        return (
            self.shader_bin
            / file_name
        )

    # ==========================================================
    # DEBUG
    # ==========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            "ProjectPaths("
            f"project_name={self.project_name!r}, "
            f"root={str(self.root)!r}"
            ")"
        )