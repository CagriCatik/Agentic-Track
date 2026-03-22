# 07.02 — Pipenv vs uv

## Overview

This is a quick housekeeping note: this section was originally recorded using **Pipenv**, while the rest of the course uses **uv**. The actual code is identical — only the dependency installation commands differ.

---

## Translation Table

| Task | Pipenv | uv |
|---|---|---|
| **Install all dependencies** | `pipenv install` | `uv sync` |
| **Add a package** | `pipenv install langchain` | `uv add langchain` |
| **Run a script** | `pipenv run python main.py` | `uv run python main.py` |
| **Activate virtual env** | `pipenv shell` | `source .venv/bin/activate` |
| **Lock file** | `Pipfile.lock` | `uv.lock` |
| **Config file** | `Pipfile` | `pyproject.toml` |

> [!NOTE]
> **uv** is the modern, Rust-based Python package manager that's significantly faster than Pipenv. It's the recommended tool throughout the rest of the course. The code, imports, and logic are completely identical regardless of which package manager you use.