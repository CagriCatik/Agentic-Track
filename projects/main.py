#!/usr/bin/env python3
"""Entry point for the local Ollama + LangChain mini-RAG project."""

from __future__ import annotations

import sys
from pathlib import Path


def _configure_import_path() -> None:
    """Avoid local module shadowing when running `python projects/main.py`."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    script_dir_str = str(script_dir)
    repo_root_str = str(repo_root)

    if script_dir_str in sys.path:
        sys.path.remove(script_dir_str)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_configure_import_path()

from projects.rag_app.app import run
from projects.rag_app.config import AppConfig, build_parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = AppConfig.from_sources(args)
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 2

    return run(config)


if __name__ == "__main__":
    raise SystemExit(main())
