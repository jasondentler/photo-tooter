# 📸 photo-tooter

**photo-tooter** is a command-line tool that posts photos to Mastodon
using **embedded EXIF metadata**.

For each image:

-   **One image → one toot**
-   Caption comes from **Title + Description** (unless overridden)
-   Alt Text comes from **Alt Text (Accessibility)** (falls back to
    Description)
-   Accepts **files and/or folders**
-   Folders are scanned for supported image formats (`.jpg`, `.png`,
    `.heic`, ...)
-   Automatically handles Mastodon media upload + status creation

Requires **exiftool** and a **Mastodon access token**.

------------------------------------------------------------------------

# 🔧 Installation

## 1. Install system dependencies

    brew install exiftool

## 2. Install the package (editable mode recommended for development)

Use quotes to avoid zsh globbing:

    pip install -e '.[dev]'

This installs:

-   `photo-tooter` CLI command\
-   Dev tools (pytest, ruff, build, pre-commit)

------------------------------------------------------------------------

# 🛠 Project Setup (Development)

Clone the repo, then:

    python3 -m venv venv
    source venv/bin/activate
    pip install -e '.[dev]'

Run tests:

    pytest

Lint:

    ruff check src

Format:

    ruff format src

Build the project:

    python -m build

Install git hooks:

    pre-commit install

Run hooks manually:

    pre-commit run --all-files

------------------------------------------------------------------------

# 🚀 Usage

After installation, the command-line tool is available as:

    photo-tooter

------------------------------------------------------------------------

## 1️⃣ Configure Mastodon credentials

Run once:

    photo-tooter configure

You will be prompted for:

-   Mastodon instance URL\
-   Access token (create one in Preferences → Development → New
    Application)

Credentials are stored at:

    ~/.config/photo-tooter/config.json

------------------------------------------------------------------------

## 2️⃣ Post images

### Post every image in a folder

    photo-tooter post /path/to/folder

The tool will:

-   Find supported image files
-   Sort them by name
-   Post each as **its own toot**

### Post specific files

    photo-tooter post image1.jpg image2.jpg

### Override caption for all images

    photo-tooter post /path/to/folder --text "Custom caption for all images"

### Change visibility

    photo-tooter post /path/to/folder --visibility unlisted

------------------------------------------------------------------------

# 🖼 Supported Image Formats

-   `.jpg`, `.jpeg`
-   `.png`
-   `.heic`, `.heif`
-   `.tif`, `.tiff`
-   `.webp`

------------------------------------------------------------------------

# 📄 Metadata Rules

photo-tooter extracts:

  -----------------------------------------------------------------------
  Metadata Field                                        Used For
  ----------------------------------------------------- -----------------
  `Title`                                               Caption text
                                                        (part 1)

  `Description`                                         Caption text
                                                        (part 2) +
                                                        fallback alt text

  `Alt Text Accessibility`                              Primary alt text

  `ExtDescrAccessibility`                               Not used
                                                        (reserved for
                                                        future)
  -----------------------------------------------------------------------

Caption logic:

-   `Title + " — " + Description`
-   or just Description if no Title
-   or just Title if no Description\
-   or you **must** use `--text` if neither exists

Alt text:

-   Uses Alt Text (Accessibility) when present\
-   Otherwise uses Description

------------------------------------------------------------------------

# 🧪 Running Tests

    pytest -q

GitHub Actions CI runs automatically on `main` and enforces:

-   Ruff lint
-   Ruff formatting
-   Pytest
-   Build success

------------------------------------------------------------------------

# 🧰 Makefile

A `Makefile` is included for convenience.

Common commands:

    make venv           # create venv
    make install-dev    # install package + dev deps
    make lint           # ruff check
    make format         # ruff format
    make test           # pytest
    make pre-commit     # run all pre-commit hooks
    make build          # build dist
    make run            # show CLI help

------------------------------------------------------------------------

# 📦 Build & Distribution

Local build:

    python -m build

Install from local build:

    pip install dist/photo-tooter-*.whl

------------------------------------------------------------------------

# 📝 License

MIT License.

------------------------------------------------------------------------

# 🤝 Contributing

Pull requests welcome! Pre-commit hooks ensure code quality. Run:

    pre-commit install

before committing.
