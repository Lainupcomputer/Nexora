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

    if (
        args.editor is not None
        and args.command is not None
    ):
        parser.error(
            "--editor cannot be combined with a subcommand."
        )

    if args.editor is not None:
        from nexora.editor import run_editor

        return run_editor(
            project_path=args.editor,
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
