import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from mastodon import Mastodon, MastodonAPIError, MastodonUnauthorizedError

APP_NAME = "photo-tooter"

CONFIG_DIR = Path(f"~/.config/{APP_NAME}").expanduser()
CONFIG_FILE = CONFIG_DIR / "config.json"

IMAGE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
    ".tif",
    ".tiff",
    ".webp",
}

# ----------------- Config ----------------- #


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        raise RuntimeError(f"Config file not found. Run `{APP_NAME} configure` first.")
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Config file is corrupted: {CONFIG_FILE}\n{e}") from e

    if "base_url" not in cfg or "access_token" not in cfg:
        raise RuntimeError(
            f"Config file {CONFIG_FILE} is missing required fields. "
            f"Run `{APP_NAME} configure` again."
        )
    return cfg


def save_config(base_url: str, access_token: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {
        "base_url": base_url.strip().rstrip("/"),
        "access_token": access_token.strip(),
    }
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    try:
        os.chmod(CONFIG_FILE, 0o600)
    except PermissionError:
        pass


def configure_command() -> None:
    print(f"=== {APP_NAME} configuration ===")
    base_url = input("Mastodon instance URL (e.g. https://mastodon.social): ").strip()
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        print("Error: URL must start with http:// or https://")
        return

    print(
        "\nCreate an application in Mastodon (Preferences → Development) "
        "and copy an access token.\n"
        "Scopes needed: at least write:statuses and write:media.\n"
    )
    access_token = input("Access token: ").strip()
    if not access_token:
        print("Error: access token cannot be empty.")
        return

    save_config(base_url, access_token)
    print(f"\nSaved config to {CONFIG_FILE}")
    print(f"You can now post with: {APP_NAME} post PATH")


def build_mastodon_client() -> Mastodon:
    cfg = load_config()
    return Mastodon(
        api_base_url=cfg["base_url"],
        access_token=cfg["access_token"],
    )


# ----------------- EXIF ----------------- #


def run_exiftool(path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "exiftool",
                "-json",
                "-Title",
                "-Description",
                "-AltTextAccessibility",
                "-ExtDescrAccessibility",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "exiftool not found. Install via: brew install exiftool"
        ) from None
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Error running exiftool on {path}: {e.stderr.strip()}"
        ) from e

    data = json.loads(result.stdout)
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"Unexpected exiftool JSON format for {path}")
    return data[0]


def _extract_lang_alt(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("en-US", "en", "x-default"):
            if key in value and isinstance(value[key], str) and value[key].strip():
                return value[key].strip()
        for v in value.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def extract_metadata(path: Path) -> tuple[str | None, str | None, str | None]:
    meta = run_exiftool(path)

    title = meta.get("Title")
    if isinstance(title, list):
        title = title[0]
    title = title.strip() if isinstance(title, str) else None

    description = meta.get("Description")
    if isinstance(description, list):
        description = description[0]
    description = description.strip() if isinstance(description, str) else None

    alt_raw = (
        meta.get("AltTextAccessibility")
        or meta.get("Alt Text Accessibility")
        or meta.get("AltTextAccessibility-en-US")
    )
    alt_text = _extract_lang_alt(alt_raw) or description

    return title, description, alt_text


def build_default_status_text(title, description):
    if title and description:
        return f"{title} — {description}"
    if description:
        return description
    if title:
        return title
    raise RuntimeError(
        "No title or description found in metadata. Use --text to specify manually."
    )


# ----------------- Image collection ----------------- #


def collect_image_paths(inputs: list[str]) -> list[Path]:
    result = []
    for raw in inputs:
        p = Path(raw).expanduser()
        if p.is_dir():
            for child in sorted(p.iterdir()):
                if child.is_file() and child.suffix.lower() in IMAGE_EXTS:
                    result.append(child)
        elif p.is_file():
            if p.suffix.lower() in IMAGE_EXTS:
                result.append(p)
        else:
            print(f"Warning: path not found: {p}")

    if not result:
        raise RuntimeError("No image files found.")

    return result


# ----------------- Posting ----------------- #


def post_single_image(
    mastodon: Mastodon,
    path: Path,
    text_override: str | None,
    visibility: str,
    scheduled_at: datetime | None = None,
) -> str:
    """
    Post (or schedule) a single image as its own toot.
    Returns the toot URL if Mastodon provides one, otherwise an empty string.

    Any Mastodon API issues are wrapped as RuntimeError so the caller
    can handle them and continue with the next image.
    """
    title, description, alt_text = extract_metadata(path)

    status_text = text_override or build_default_status_text(title, description)

    # Upload media
    try:
        media = mastodon.media_post(
            str(path),
            description=alt_text or None,
        )
    except (MastodonAPIError, MastodonUnauthorizedError) as e:
        # MastodonAPIError.args is typically:
        # ('Mastodon API returned error', status_code, reason, error_msg)
        if len(e.args) >= 4 and isinstance(e.args[3], str):
            api_msg = e.args[3]
        else:
            api_msg = str(e)

        if "less than 16 MB" in api_msg:
            hint = (
                "File is larger than this instance's max media size (e.g. 16 MB). "
                "Export a smaller version and try again."
            )
        elif "images are not supported" in api_msg:
            hint = (
                "Image resolution is too large for this instance. "
                "Export a version with a smaller long edge "
                "(for example, 4000–6000 px) and try again."
            )
        else:
            hint = api_msg

        raise RuntimeError(f"Error uploading {path.name}: {hint}") from e

    media_id = media["id"]

    # Post or schedule toot
    try:
        status = mastodon.status_post(
            status=status_text,
            media_ids=[media_id],
            visibility=visibility,
            scheduled_at=scheduled_at,  # ✅ datetime or None, not str
        )
    except (MastodonAPIError, MastodonUnauthorizedError) as e:
        raise RuntimeError(f"Error posting status for {path.name}: {e}") from e

    # For scheduled statuses, URL may not be present yet
    url = status.get("url")
    return url or ""


def post_images_command(inputs, text_override, visibility):
    mastodon = build_mastodon_client()
    paths = collect_image_paths(inputs)

    total = len(paths)
    print(f"Found {total} image(s) to post.")

    # Track successes and failures
    posted: list[tuple[Path, str, datetime | None]] = []
    failed: list[tuple[Path, str]] = []

    # Start scheduling timestamps in UTC.
    # First toot is immediate; each subsequent toot is 10 minutes after the previous.
    start_time = datetime.now(UTC)

    for idx, p in enumerate(paths, start=1):
        if idx == 1:
            scheduled_at = None  # first toot: immediate
            sched_label = "immediately"
        else:
            scheduled_at = start_time + timedelta(minutes=10 * (idx - 1))
            sched_label = scheduled_at.isoformat()

        print(f"\n[{idx}/{total}] Posting {p.name} (scheduled at {sched_label})...")

        try:
            url = post_single_image(
                mastodon=mastodon,
                path=p,
                text_override=text_override,
                visibility=visibility,
                scheduled_at=scheduled_at,
            )
        except RuntimeError as e:
            msg = str(e)
            print(f"Error: {msg}")
            failed.append((p, msg))
            continue

        if url:
            print(f"Done → {url}")
        else:
            if scheduled_at is None:
                print("Done → (no URL returned)")
            else:
                print(f"Done → (scheduled for {scheduled_at.isoformat()})")

        posted.append((p, url, scheduled_at))

    # After the loop, write helper files so you can easily retry failures
    cwd = Path.cwd()

    if posted:
        posted_file = cwd / "photo-tooter-posted.txt"
        with posted_file.open("w", encoding="utf-8") as f:
            for path, url, sched in posted:
                sched_str = sched.isoformat() if sched is not None else ""
                # path, url (may be empty if scheduled), scheduled_at (maybe empty)
                f.write(f"{path}\t{url}\t{sched_str}\n")
        print(
            f"\n✅ Posted/scheduled {len(posted)}/{total} image(s). "
            f"Details written to: {posted_file}"
        )

    if failed:
        failed_file = cwd / "photo-tooter-failed.txt"
        with failed_file.open("w", encoding="utf-8") as f:
            for path, _msg in failed:
                # One path per line so it can be reused directly on the CLI
                f.write(f"{path}\n")
        print(f"⚠️ {len(failed)} image(s) failed. Paths written to: {failed_file}")
        print(
            "You can retry just the failures with:\n"
            f"  photo-tooter post $(cat {failed_file.name})"
        )
    else:
        print(f"\n🎉 All {total} image(s) posted/scheduled successfully.")
