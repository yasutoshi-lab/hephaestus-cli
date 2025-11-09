# Pytest Execution Guide

This document explains how to run the Hephaestus test suite with `uv`.

## Prerequisites

- Python 3.10 or later
- `uv` installed (https://github.com/astral-sh/uv)
- You are located in the project root, e.g. `/home/ubuntu/python_project/Hephaestus`

## 1. Provision the virtual environment

On the first run, `uv` automatically creates `.venv`. If `pytest` is not yet installed, run:

```bash
uv pip install pytest
```

When dependencies are added to `pyproject.toml` / `uv.lock`, sync them with:

```bash
uv sync
```

## 2. Run the tests

Execute the full test suite:

```bash
uv run pytest
```

To target a specific directory or file, provide the path:

```bash
uv run pytest test/unit/test_communication.py
uv run pytest test/integration
```

## 3. Troubleshooting

- `pytest: command not found`: reinstall with `uv pip install pytest`
- To use an existing virtualenv, activate it (`source .venv/bin/activate`) and run `pytest` directly
- After dependency changes, `uv sync` ensures the lockfile matches the environment

## 4. Notes

- `uv run` handles environment creation and caching automatically
- As of 2025-11-09 the suite consists of 30 tests under `test/`


