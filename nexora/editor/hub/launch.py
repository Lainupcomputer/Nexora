from __future__ import annotations

import subprocess
import sys

from nexora.editor.hub.recent_projects import remember_project


class HubLaunchMixin:
    """Launch specialized Nexora editor processes."""

    def _open_editor(self, flag: str) -> None:
        command = [
            sys.executable,
            "-m",
            "nexora",
            flag,
            str(self.project_path),
        ]

        try:
            subprocess.Popen(command, cwd=str(self.project_path))
        except OSError as exc:
            self.status_label.text = f"Could not start editor: {exc}"
            return

        names = {
            "--editor": "Nexora Main Editor",
            "--tilemapedit": "TileMap Editor",
            "--itemedit": "Item Editor",
            "--cutsceneedit": "Cutscene Editor",
            "--audioedit": "Audio Editor",
        }
        self.status_label.text = f"Started {names.get(flag, flag)}"
        remember_project(self.project_path)
