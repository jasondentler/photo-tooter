import argparse

from .metadata import configure_command, post_images_command


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photo-tooter",
        description=(
            "Post one toot per photo to Mastodon using embedded metadata. "
            "Accepts files and/or folders."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # configure
    configure_parser = subparsers.add_parser(
        "configure",
        help="Set up Mastodon instance URL and access token.",
    )
    configure_parser.set_defaults(func=lambda args: configure_command())

    # post
    post_parser = subparsers.add_parser(
        "post",
        help="Post each image as its own toot.",
    )
    post_parser.add_argument(
        "paths",
        nargs="+",
        help="File(s) and/or folder(s) containing images.",
    )
    post_parser.add_argument(
        "-t",
        "--text",
        dest="text",
        default=None,
        help="Optional toot text override.",
    )
    post_parser.add_argument(
        "-v",
        "--visibility",
        choices=["public", "unlisted", "private", "direct"],
        default="public",
        help="Visibility of each toot (default: public).",
    )
    post_parser.set_defaults(
        func=lambda args: post_images_command(
            inputs=args.paths,
            text_override=args.text,
            visibility=args.visibility,
        )
    )

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"Error: {e}")
        raise SystemExit(1) from None
