"""Modular local RAG application package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import run
    from .config import AppConfig, build_parser

__all__ = ["AppConfig", "build_parser", "run"]


def __getattr__(name: str):
    if name == "run":
        from .app import run as value
        return value
    if name == "AppConfig":
        from .config import AppConfig as value
        return value
    if name == "build_parser":
        from .config import build_parser as value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
