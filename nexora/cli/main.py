from __future__ import annotations

import argparse
import sys

from nexora.cli.project import create_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexora",
        description="Nexora Engine command-line tools.",
    )

    parser.add_argument(
        "--editor",
        nargs="?",
        const=".",
        default=None,
        metavar="PROJECT",
        help=(
            "Start the Nexora Editor. "
            "Without PROJECT the current directory is opened."
        ),
    )

    parser.add_argument(
        "--editor-tools",
        nargs="?",
        const=".",
        default=None,
        metavar="PROJECT",
        help=(
            "Open the Nexora Editor Tools launcher. "
            "Without PROJECT the current directory is opened."
        ),
    )

    parser.add_argument(
        "--tilemapedit",
        nargs="?",
        const=".",
        default=None,
        metavar="PROJECT",
        help=(
            "Start the standalone TileMap Editor. "
            "Without PROJECT the current directory is opened."
        ),
    )

    parser.add_argument(
        "--itemedit",
        nargs="?",
        const=".",
        default=None,
        metavar="PROJECT",
        help=(
            "Start the standalone Item Editor. "
            "Without PROJECT the current directory is opened."
        ),
    )

    parser.add_argument(
        "--cutsceneedit",
        "--cutscene-editor",
        dest="cutsceneedit",
        nargs="?",
        const=".",
        default=None,
        metavar="PROJECT",
        help=(
            "Start the standalone Cutscene Editor. "
            "Without PROJECT the current directory is opened."
        ),
    )

    parser.add_argument(
        "--cutscene",
        default=None,
        metavar="ASSET",
        help="Open this .ncutscene asset in the standalone Cutscene Editor.",
    )

    parser.add_argument(
        "--tilemap",
        default=None,
        metavar="ASSET",
        help="Open this .ntmap asset in the standalone TileMap Editor.",
    )

    parser.add_argument(
        "--item",
        default=None,
        metavar="ASSET",
        help="Open this .nitem asset in the standalone Item Editor.",
    )

    # Kept as a parsing compatibility alias for older scripts.  The
    # standalone editor now accepts TileMap assets, not scene files.
    parser.add_argument(
        "--scene",
        default=None,
        metavar="LEGACY_ASSET",
        help=argparse.SUPPRESS,
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    create_parser = subparsers.add_parser(
        "create",
        help="Create a new Nexora game project.",
    )

    create_parser.add_argument(
        "name",
        help="Name of the game project.",
    )

    create_parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Directory where the project should be created.",
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    editor_modes = [
        name
        for name, value in (
            ("--editor", args.editor),
            ("--editor-tools", args.editor_tools),
            ("--tilemapedit", args.tilemapedit),
            ("--itemedit", args.itemedit),
            ("--cutsceneedit", args.cutsceneedit),
        )
        if value is not None
    ]
    if editor_modes and args.command is not None:
        parser.error(
            f"{'/'.join(editor_modes)} cannot be combined with a subcommand."
        )
    if len(editor_modes) > 1:
        parser.error("Only one editor mode can be selected at a time.")

    if args.tilemap is not None and args.scene is not None:
        parser.error("--tilemap and legacy --scene cannot be used together.")

    selected_tilemap = args.tilemap if args.tilemap is not None else args.scene
    if selected_tilemap is not None and args.tilemapedit is None:
        parser.error("--tilemap can only be used with --tilemapedit.")

    if args.item is not None and args.itemedit is None:
        parser.error("--item can only be used with --itemedit.")

    if args.cutscene is not None and args.cutsceneedit is None:
        parser.error("--cutscene can only be used with --cutsceneedit.")

    if args.editor is not None:
        from nexora.editor import run_editor

        return run_editor(
            project_path=args.editor,
        )

    if args.editor_tools is not None:
        from nexora.editor import run_editor_tools

        return run_editor_tools(
            project_path=args.editor_tools,
        )

    if args.tilemapedit is not None:
        from nexora.editor import run_standalone_tilemap_editor

        return run_standalone_tilemap_editor(
            project_path=args.tilemapedit,
            tilemap_path=selected_tilemap,
        )

    if args.itemedit is not None:
        from nexora.editor import run_item_editor

        return run_item_editor(
            project_path=args.itemedit,
            item_path=args.item,
        )

    if args.cutsceneedit is not None:
        from nexora.editor import run_cutscene_editor

        return run_cutscene_editor(
            project_path=args.cutsceneedit,
            cutscene_path=args.cutscene,
        )

    if args.command == "create":
        return create_project(
            name=args.name,
            path=args.path,
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
