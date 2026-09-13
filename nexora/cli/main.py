from __future__ import annotations

import argparse
import sys

from nexora.cli.project import create_project


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="nexora",
        description="Nexora Engine command-line tools.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
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

    args = parser.parse_args()

    if args.command == "create":
        return create_project(
            name=args.name,
            path=args.path,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())