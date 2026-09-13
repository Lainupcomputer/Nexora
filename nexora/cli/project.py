from __future__ import annotations

import re
from pathlib import Path


PROJECT_TEMPLATE = """\
from nexora import ...


def main() -> None:
    pass


if __name__ == "__main__":
    main()
"""


GITIGNORE_TEMPLATE = """\
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
"""


README_TEMPLATE = """\
# {name}

A game built with Nexora Engine.

Run the game with:

    python main.py
"""


def _valid_project_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", name))


def create_project(name: str, path: str = ".") -> int:
    if not _valid_project_name(name):
        print(
            f"Error: Invalid project name: {name!r}"
        )
        print(
            "Project names may contain letters, numbers, '-' and '_'."
        )
        return 1

    root = Path(path).resolve() / name

    if root.exists():
        print(f"Error: Project already exists: {root}")
        return 1

    print()
    print("=" * 40)
    print(" Nexora Engine - Create Project")
    print("=" * 40)
    print()
    print(f"Creating project: {name}")
    print()

    directories = [
        root / "assets",
        root / "assets" / "sprites",
        root / "assets" / "audio",
        root / "assets" / "fonts",
        root / "scenes",
        root / "scripts",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    files = {
        root / "main.py": PROJECT_TEMPLATE,
        root / "README.md": README_TEMPLATE.format(name=name),
        root / ".gitignore": GITIGNORE_TEMPLATE,
    }

    for file_path, content in files.items():
        file_path.write_text(content, encoding="utf-8")

    print(f"✓ Created {root}")
    print("✓ Created main.py")
    print("✓ Created assets/")
    print("✓ Created assets/sprites/")
    print("✓ Created assets/audio/")
    print("✓ Created assets/fonts/")
    print("✓ Created scenes/")
    print("✓ Created scripts/")
    print("✓ Created README.md")
    print("✓ Created .gitignore")
    print()
    print("Project created successfully!")
    print()
    print("Next steps:")
    print(f"  cd {name}")
    print("  python main.py")
    print()

    return 0