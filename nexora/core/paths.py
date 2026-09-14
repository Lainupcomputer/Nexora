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


# ==============================================================
# PROJECT PATHS
# ==============================================================


class ProjectPaths:
    """
    Central filesystem paths for a Nexora project.

    Engine defaults:

        nexora/core/defaults/

    User project data:

        Documents/<project_name>/

    Structure:

        Documents/<project_name>/
            settings/
            saves/
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
        # Nexora
        # ======================================================

        self.defaults = (
            DEFAULTS_DIR
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

        self.settings = (
            self.root
            / "settings"
        )

        self.saves = (
            self.root
            / "saves"
        )

    # ==========================================================
    # CREATE
    # ==========================================================

    def ensure(
        self,
    ) -> None:
        """
        Create all Nexora project directories.
        """

        self.settings.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.saves.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ==========================================================
    # FILE HELPERS
    # ==========================================================

    def default_file(
        self,
        file_name: str,
    ) -> Path:
        return (
            self.defaults
            / file_name
        )

    def settings_file(
        self,
        file_name: str,
    ) -> Path:
        return (
            self.settings
            / file_name
        )

    def save_file(
        self,
        file_name: str,
    ) -> Path:
        return (
            self.saves
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