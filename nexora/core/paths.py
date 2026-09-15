from __future__ import annotations

import shutil
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

ENGINE_SHADER_BIN_DIR = (
    ENGINE_SHADER_DIR
    / "bin"
)


# ==============================================================
# PROJECT PATHS
# ==============================================================


class ProjectPaths:
    """
    Central filesystem paths for a Nexora project.

    Engine resources:

        nexora/core/defaults/
        nexora/rendering/shaders/bin/

    User project data:

        Documents/<project_name>/

    Structure:

        Documents/<project_name>/
            settings/
            saves/
            shaders/
                bin/

    Compiled engine shaders are deployed automatically from:

        nexora/rendering/shaders/bin/

    to:

        Documents/<project_name>/shaders/bin/
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

        self.engine_shader_bin = (
            ENGINE_SHADER_BIN_DIR
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
    # SHADER DEPLOYMENT
    # ==========================================================

    def deploy_shaders(
        self,
    ) -> int:
        """
        Deploy compiled Nexora shaders into the project runtime
        shader directory.

        Source:

            nexora/rendering/shaders/bin/

        Destination:

            Documents/<project_name>/shaders/bin/

        A shader is copied when:

            - it does not exist in the destination
            - its contents differ from the engine shader

        Returns the number of copied shader files.
        """

        if not self.engine_shader_bin.is_dir():
            raise FileNotFoundError(
                "Nexora engine shader directory "
                "does not exist: "
                f"{self.engine_shader_bin}"
            )

        self.shader_bin.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_shaders = sorted(
            path
            for path in self.engine_shader_bin.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                == ".spv"
            )
        )

        if not source_shaders:
            raise FileNotFoundError(
                "No compiled .spv shaders found in: "
                f"{self.engine_shader_bin}"
            )

        copied = 0

        for source in source_shaders:
            destination = (
                self.shader_bin
                / source.name
            )

            if self._files_equal(
                source,
                destination,
            ):
                continue

            shutil.copy2(
                source,
                destination,
            )

            copied += 1

        return copied

    # ==========================================================
    # FILE COMPARISON
    # ==========================================================

    @staticmethod
    def _files_equal(
        source: Path,
        destination: Path,
    ) -> bool:
        """
        Return True when two files contain identical bytes.

        File sizes are compared first to avoid unnecessary
        reads for obviously different files.
        """

        if not destination.is_file():
            return False

        try:
            source_stat = (
                source.stat()
            )

            destination_stat = (
                destination.stat()
            )

        except OSError:
            return False

        if (
            source_stat.st_size
            != destination_stat.st_size
        ):
            return False

        try:
            with source.open(
                "rb"
            ) as source_file:
                with destination.open(
                    "rb"
                ) as destination_file:
                    while True:
                        source_chunk = (
                            source_file.read(
                                64 * 1024
                            )
                        )

                        destination_chunk = (
                            destination_file.read(
                                64 * 1024
                            )
                        )

                        if (
                            source_chunk
                            != destination_chunk
                        ):
                            return False

                        if not source_chunk:
                            return True

        except OSError:
            return False

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
        Return a deployed compiled shader file.

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