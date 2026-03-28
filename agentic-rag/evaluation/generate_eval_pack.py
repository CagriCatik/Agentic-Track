#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.knowledge.ingestion import load_silver
from src.config import get_settings, resolve_path

def extract_keywords(text: str) -> list[str]:
    return [w for w in text.split() if w.isalnum() and len(w) > 3]

class DummySource:
    def __init__(self, name: str, title: str):
        self.source_name = name
        self.title = title
        self.author = ""
        self.segments: list[str] = []

def load_sources() -> list[DummySource]:
    settings = get_settings()
    docs = load_silver(resolve_path(settings.data.silver_dir))
    
    sources: dict[str, DummySource] = {}
    for doc in docs:
        src = doc.metadata.get("source_file", "unknown")
        if src not in sources:
            sources[src] = DummySource(src, src)
        sources[src].segments.append(doc.page_content)
    return list(sources.values())

def _humanize_source_name(source_name: str) -> str:
    return Path(source_name).stem.replace("_", " ").replace("-", " ").strip() or source_name

def _best_title(source_name: str, title: str) -> str:
    cleaned_title = " ".join(title.split()).strip()
    if len(cleaned_title.split()) >= 2:
        return cleaned_title
    return _humanize_source_name(source_name)

def _author_aliases(author: str) -> list[str]:
    if not author: return []
    aliases = [" ".join(author.split()).strip()]
    for part in author.replace(";", ",").split(","):
        candidate = " ".join(part.split()).strip()
        if candidate and candidate not in aliases:
            aliases.append(candidate)
    return [alias for alias in aliases if alias]

def _pick_excerpt(text: str) -> str:
    candidates: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()).strip()
        if len(line) < 60:
            continue
        lowered = line.casefold()
        if "urheberrechtlich" in lowered or "copyright" in lowered or "bereitgestellt von" in lowered:
            continue
        if len(extract_keywords(line)) < 6:
            continue
        candidates.append(line)
        if len(candidates) >= 6:
            break

    for candidate in candidates:
        if len(candidate) <= 220:
            return candidate
        return candidate[:220].rsplit(" ", 1)[0].strip(" ,.;:-")

    filtered_words = [
        word
        for word in text.split()
        if normalize_word(word) not in {"copyright", "urheberrechtlich", "bereitgestellt", "material"}
    ]
    collapsed = " ".join(filtered_words) or " ".join(text.split())
    return collapsed[:180].rsplit(" ", 1)[0].strip(" ,.;:-")

def normalize_word(word: str) -> str:
    return "".join(char for char in word.casefold() if char.isalnum())

def _make_fake_title(existing_tokens: set[str]) -> str:
    base = "Synthetic Atlas of Unindexed Knowledge"
    suffix = 101
    while True:
        candidate = f"{base} {suffix}"
        if candidate.casefold() not in existing_tokens:
            return candidate
        suffix += 1

def _make_fake_acronym(existing_tokens: set[str]) -> str:
    seed = 317
    while True:
        candidate = f"ZXQ-{seed}"
        if candidate.casefold() not in existing_tokens:
            return candidate
        seed += 1

def build_pack(*, corpus_dir: Path, max_sources: int) -> dict[str, Any]:
    loaded = load_sources()[:max_sources]

    existing_tokens = {
        source.title.casefold()
        for source in loaded
        if source.title
    }
    existing_tokens.update(source.source_name.casefold() for source in loaded)

    cases: list[dict[str, Any]] = []
    case_index = 1

    for source in loaded:
        title = _best_title(source.source_name, source.title or source.source_name)
        title_aliases = [title, source.source_name, _humanize_source_name(source.source_name)]
        cases.append(
            {
                "id": f"C{case_index:03d}",
                "type": "title_lookup",
                "prompt": f"What is the exact title of the indexed source file `{source.source_name}`? Cite the supporting block.",
                "checks": [
                    {"kind": "contains_any", "values": title_aliases},
                    {"kind": "citation"},
                ],
                "metadata": {
                    "source_name": source.source_name,
                    "title": title,
                },
            }
        )
        case_index += 1

        if source.author:
            cases.append(
                {
                    "id": f"C{case_index:03d}",
                    "type": "author_lookup",
                    "prompt": f"Who is the author of the indexed document `{title}`? Cite the supporting block.",
                    "checks": [
                        {"kind": "contains_any", "values": _author_aliases(source.author)},
                        {"kind": "citation"},
                    ],
                    "metadata": {
                        "title": title,
                        "author": source.author,
                    },
                }
            )
            case_index += 1

        segment_text = "\n".join(segment for segment in source.segments[:4] if segment and segment.strip())
        excerpt = _pick_excerpt(segment_text)
        if excerpt:
            cases.append(
                {
                    "id": f"C{case_index:03d}",
                    "type": "source_grounding",
                    "prompt": f"Which indexed source best matches this excerpt: \"{excerpt}\"? Answer with the best matching title or source name and cite the supporting block.",
                    "checks": [
                        {"kind": "contains_any", "values": title_aliases},
                        {"kind": "citation"},
                    ],
                    "metadata": {
                        "title": title,
                        "source_name": source.source_name,
                        "excerpt": excerpt,
                    },
                }
            )
            case_index += 1

    fake_title = _make_fake_title(existing_tokens)
    fake_acronym = _make_fake_acronym(existing_tokens)

    cases.extend(
        [
            {
                "id": f"C{case_index:03d}",
                "type": "negative_missing_title",
                "prompt": f"Is there an indexed source titled `{fake_title}`? If the indexed sources do not support it, say you don't know based on the indexed sources.",
                "checks": [{"kind": "abstain"}],
                "metadata": {"missing_title": fake_title},
            },
            {
                "id": f"C{case_index + 1:03d}",
                "type": "negative_missing_author",
                "prompt": f"Who is the author of the indexed document `{fake_title}`? If the indexed sources do not support it, say you don't know based on the indexed sources.",
                "checks": [{"kind": "abstain"}],
                "metadata": {"missing_title": fake_title},
            },
            {
                "id": f"C{case_index + 2:03d}",
                "type": "negative_missing_acronym",
                "prompt": f"What does `{fake_acronym}` mean in the indexed sources? If the indexed sources do not support it, say you don't know based on the indexed sources.",
                "checks": [{"kind": "abstain"}],
                "metadata": {"missing_acronym": fake_acronym},
            },
            {
                "id": f"C{case_index + 3:03d}",
                "type": "negative_external_fact",
                "prompt": "What is the release date of the product `Orchid Ledger Cloud` in the indexed sources? If the indexed sources do not support it, say you don't know based on the indexed sources.",
                "checks": [{"kind": "abstain"}],
                "metadata": {"external_fact": "Orchid Ledger Cloud release date"},
            },
        ]
    )

    return {
        "pack_id": "corpus_agnostic_eval_v1",
        "version": "1.0.0",
        "corpus_dir": str(corpus_dir),
        "source_count": len(loaded),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a corpus-agnostic evaluation pack from the current corpus.")
    parser.add_argument("--corpus-dir", default=str(repo_root / "corbus"), help="Corpus directory")
    parser.add_argument("--max-sources", type=int, default=4, help="Maximum number of corpus sources to sample")
    parser.add_argument("--out", default=str(repo_root / "evaluation" / "corpus_eval_pack.json"), help="Output pack path")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.exists():
        print(f"Error: corpus directory not found: {corpus_dir}", file=sys.stderr)
        return 2

    pack = build_pack(corpus_dir=corpus_dir, max_sources=max(1, args.max_sources))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated evaluation pack with {len(pack['cases'])} cases at {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
