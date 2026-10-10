from __future__ import annotations

import json
from pathlib import Path


_STATE_DIR = Path.home() / ".nexora"
_STATE_FILE = _STATE_DIR / "editor_hub.json"
_MAX_RECENT = 10


def load_recent_projects() -> list[Path]:
    """Return existing recent project directories, newest first."""

    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []

    raw_projects = data.get("recent_projects", []) if isinstance(data, dict) else []
    result: list[Path] = []
    seen: set[Path] = set()

    for value in raw_projects:
        try:
            path = Path(str(value)).expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if path in seen or not path.is_dir():
            continue
        seen.add(path)
        result.append(path)
        if len(result) >= _MAX_RECENT:
            break

    return result


def save_recent_projects(projects: list[Path]) -> None:
    """Persist a normalized recent-project list."""

    normalized: list[str] = []
    seen: set[Path] = set()
    for value in projects:
        try:
            path = Path(value).expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if path in seen or not path.is_dir():
            continue
        seen.add(path)
        normalized.append(str(path))
        if len(normalized) >= _MAX_RECENT:
            break

    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps({"recent_projects": normalized}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # Recent projects are convenience state. Failure must never prevent
        # the editor hub from opening.
        return


def remember_project(path: str | Path) -> list[Path]:
    """Move *path* to the front of the recent-project list and persist it."""

    project = Path(path).expanduser().resolve()
    projects = [entry for entry in load_recent_projects() if entry != project]
    if project.is_dir():
        projects.insert(0, project)
    projects = projects[:_MAX_RECENT]
    save_recent_projects(projects)
    return projects


def forget_project(path: str | Path) -> list[Path]:
    project = Path(path).expanduser().resolve()
    projects = [entry for entry in load_recent_projects() if entry != project]
    save_recent_projects(projects)
    return projects


__all__ = [
    "forget_project",
    "load_recent_projects",
    "remember_project",
    "save_recent_projects",
]
