# Makefile for photo-tooter

# -------------------------
# Config
# -------------------------

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
PYTEST := $(VENV)/bin/pytest
PRE_COMMIT := $(VENV)/bin/pre-commit

# Default target
.PHONY: help
help:
	@echo "photo-tooter Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make venv           Create virtual environment (./venv)"
	@echo "  make install        Install package (editable)"
	@echo "  make install-dev    Install package with dev extras"
	@echo "  make lint           Run Ruff lint checks"
	@echo "  make format         Run Ruff formatter"
	@echo "  make test           Run pytest"
	@echo "  make pre-commit     Run pre-commit on all files"
	@echo "  make pre-commit-install  Install pre-commit git hook"
	@echo "  make build          Build distribution (sdist + wheel)"
	@echo "  make clean          Remove build artifacts"
	@echo "  make distclean      Clean build artifacts and venv"
	@echo "  make run            Show CLI help (photo-tooter --help)"

# -------------------------
# Environment / install
# -------------------------

$(VENV):
	python3 -m venv $(VENV)
	@echo ""
	@echo "Virtual environment created in ./$(VENV)"
	@echo "Activate it with:"
	@echo "  source $(VENV)/bin/activate"

.PHONY: venv
venv: $(VENV)

.PHONY: install
install: $(VENV)
	$(PIP) install -e .

.PHONY: install-dev
install-dev: $(VENV)
	$(PIP) install -e '.[dev]'

# -------------------------
# Quality checks
# -------------------------

.PHONY: lint
lint: $(VENV)
	$(RUFF) check src tests

.PHONY: format
format: $(VENV)
	$(RUFF) format src tests

.PHONY: test
test: $(VENV)
	$(PYTEST)

.PHONY: pre-commit
pre-commit: $(VENV)
	$(PRE_COMMIT) run --all-files

.PHONY: pre-commit-install
pre-commit-install: $(VENV)
	$(PRE_COMMIT) install

# -------------------------
# Build / clean
# -------------------------

.PHONY: build
build: $(VENV)
	$(PYTHON) -m build

.PHONY: clean
clean:
	rm -rf build/ dist/ *.egg-info

.PHONY: distclean
distclean: clean
	rm -rf $(VENV)

# -------------------------
# Convenience
# -------------------------

.PHONY: run
run: $(VENV)
	$(VENV)/bin/photo-tooter --help
