"""Citation normalization and reference selection helpers."""

from __future__ import annotations

import re
from typing import Any

INLINE_CITATION_PATTERN = re.compile(
    r"(?:\[(?P<square>\d+)(?:[^\]]*)\]|\u3010\s*(?P<fullwidth>\d+)(?:[^\u3011]*)\u3011)"
)
DISPLAY_SPACE_PATTERN = re.compile(r"[\u00A0\u2000-\u200B\u202F\u205F\u2060\u3000]")


def normalize_inline_citations(answer: str) -> tuple[str, list[int]]:
    """Normalize model citation variants to [n] and return cited indices."""
    if not answer:
        return "", []

    answer = DISPLAY_SPACE_PATTERN.sub(" ", answer)

    cited_indices: list[int] = []
    seen: set[int] = set()

    def repl(match: re.Match[str]) -> str:
        raw_index = match.group("square") or match.group("fullwidth") or "0"
        index = int(raw_index)
        if index > 0 and index not in seen:
            seen.add(index)
            cited_indices.append(index)
        return f"[{index}]"

    normalized = INLINE_CITATION_PATTERN.sub(repl, answer)
    normalized = re.sub(r"\[(\d+)\](?:\s*\[\1\])+", r"[\1]", normalized)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    return normalized, cited_indices


def build_cited_reference_lines(docs: list[Any], cited_indices: list[int]) -> list[str]:
    if not docs or not cited_indices:
        return []

    lines: list[str] = []
    for index in cited_indices:
        doc_index = index - 1
        if doc_index < 0 or doc_index >= len(docs):
            continue
        metadata = getattr(docs[doc_index], "metadata", None)
        if not isinstance(metadata, dict):
            continue

        title = metadata.get("title") or metadata.get("source_name") or metadata.get("source_path") or "Unknown"
        author = metadata.get("author") or ""
        page = metadata.get("page", "?")
        source = metadata.get("source_name") or metadata.get("source_path") or metadata.get("source") or "Unknown"
        author_part = f" by {author}" if author and str(author).casefold() != "unknown" else ""
        lines.append(f"[{index}] **{title}**{author_part} (Page {page}) - `{source}`")
    return lines
