"""Content-hash based change detection for incremental ingestion."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.config import get_settings, resolve_path
from src.knowledge.schemas import ManifestEntry


def _hash_file(path: Path) -> str:
    """Compute SHA-256 hash of a file in 8KB chunks."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha.update(block)
    return sha.hexdigest()


def load_manifest(manifest_dir: Path | None = None) -> dict[str, ManifestEntry]:
    """Load the ingestion manifest from disk."""
    if manifest_dir is None:
        manifest_dir = resolve_path(get_settings().data.manifest_dir)

    manifest_file = manifest_dir / "manifest.json"
    if not manifest_file.exists():
        return {}

    with open(manifest_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return {k: ManifestEntry(**v) for k, v in raw.items()}


def save_manifest(
    manifest: dict[str, ManifestEntry], manifest_dir: Path | None = None
) -> None:
    """Persist the ingestion manifest to disk."""
    if manifest_dir is None:
        manifest_dir = resolve_path(get_settings().data.manifest_dir)

    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "manifest.json"

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump({k: v.model_dump() for k, v in manifest.items()}, f, indent=2)


def get_changed_files(search_dirs: list[Path] | None = None) -> list[Path]:
    """Return new or changed files from the specified directories."""
    if search_dirs is None:
        search_dirs = [resolve_path("../corpus")]

    manifest = load_manifest()
    changed: list[Path] = []

    for sdir in search_dirs:
        if not sdir.exists():
            continue
        
        # Recursive scan for supported extensions
        files = []
        for ext in ["*.pdf", "*.md", "*.html", "*.htm"]:
            files.extend(list(sdir.rglob(ext)))
            
        for file_path in sorted(files):
            current_hash = _hash_file(file_path)
            
            # Use relative path as key to avoid collisions with same filename in different folders
            manifest_key = str(file_path.absolute())
            prev = manifest.get(manifest_key)

            if prev is None or prev.file_hash != current_hash:
                changed.append(file_path)

    return changed


def update_manifest_entry(
    filename: str, file_hash: str, num_chunks: int
) -> ManifestEntry:
    """Create or update a manifest entry for a processed PDF."""
    return ManifestEntry(
        filename=filename,
        file_hash=file_hash,
        num_chunks=num_chunks,
        last_ingested=datetime.now(timezone.utc).isoformat(),
    )
