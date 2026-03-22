"""SQLite FTS catalog for exact chunk lookup and hybrid retrieval."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from langchain_core.documents import Document

CATALOG_DB_NAME = "chunk_catalog.sqlite3"
CATALOG_SCHEMA_VERSION = 1


def get_catalog_path(vector_db_dir: str | Path) -> Path:
    return Path(vector_db_dir) / CATALOG_DB_NAME


def catalog_is_compatible(db_path: Path) -> bool:
    if not db_path.exists():
        return False

    try:
        with closing(_connect(db_path)) as conn:
            row = conn.execute(
                "SELECT value FROM catalog_meta WHERE key = 'schema_version'"
            ).fetchone()
    except sqlite3.DatabaseError:
        return False

    if row is None:
        return False

    try:
        return int(row["value"]) == CATALOG_SCHEMA_VERSION
    except (TypeError, ValueError):
        return False


def reset_catalog(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()


def initialize_catalog(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(db_path)) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS catalog_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                source_key TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_stem TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                page INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_source_key ON chunks(source_key);
            CREATE INDEX IF NOT EXISTS idx_chunks_source_name ON chunks(source_name);

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                title,
                author,
                source_name,
                source_stem,
                content,
                tokenize='unicode61 remove_diacritics 2'
            );
            """
        )
        conn.execute(
            """
            INSERT INTO catalog_meta(key, value)
            VALUES('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(CATALOG_SCHEMA_VERSION),),
        )
        conn.commit()


def upsert_documents(db_path: Path, ids: list[str], documents: list[Document]) -> None:
    if not ids or not documents:
        return

    initialize_catalog(db_path)
    delete_chunk_ids(db_path, ids)

    rows = []
    for chunk_id, document in zip(ids, documents):
        metadata = document.metadata or {}
        source_name = str(metadata.get("source_name", ""))
        source_stem = Path(source_name).stem
        rows.append(
            (
                chunk_id,
                str(metadata.get("source_key", "")),
                str(metadata.get("source_path", "")),
                source_name,
                source_stem,
                str(metadata.get("title", "")),
                str(metadata.get("author", "")),
                int(metadata.get("page", 0)),
                int(metadata.get("chunk", 0)),
                document.page_content,
            )
        )

    with closing(_connect(db_path)) as conn:
        conn.executemany(
            """
            INSERT INTO chunks(
                chunk_id,
                source_key,
                source_path,
                source_name,
                source_stem,
                title,
                author,
                page,
                chunk_index,
                content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.executemany(
            """
            INSERT INTO chunks_fts(
                chunk_id,
                title,
                author,
                source_name,
                source_stem,
                content
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(row[0], row[5], row[6], row[3], row[4], row[9]) for row in rows],
        )
        conn.commit()


def delete_chunk_ids(db_path: Path, ids: list[str]) -> int:
    if not ids or not db_path.exists():
        return 0

    deleted = 0
    with closing(_connect(db_path)) as conn:
        for batch in _batched(ids, 256):
            placeholders = ",".join("?" for _ in batch)
            conn.execute(
                f"DELETE FROM chunks WHERE chunk_id IN ({placeholders})",
                batch,
            )
            conn.execute(
                f"DELETE FROM chunks_fts WHERE chunk_id IN ({placeholders})",
                batch,
            )
            deleted += len(batch)
        conn.commit()
    return deleted


def search_catalog(
    db_path: Path,
    *,
    expressions: list[str],
    limit: int,
) -> list[tuple[Document, float]]:
    if not expressions or not db_path.exists():
        return []

    seen: dict[str, tuple[Document, float]] = {}

    with closing(_connect(db_path)) as conn:
        for expression in expressions:
            try:
                rows = conn.execute(
                    """
                    SELECT
                        c.chunk_id,
                        c.source_key,
                        c.source_path,
                        c.source_name,
                        c.title,
                        c.author,
                        c.page,
                        c.chunk_index,
                        c.content,
                        bm25(chunks_fts) AS rank
                    FROM chunks_fts
                    JOIN chunks AS c ON c.chunk_id = chunks_fts.chunk_id
                    WHERE chunks_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (expression, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                continue

            for row in rows:
                chunk_id = row["chunk_id"]
                score = float(row["rank"])
                current = seen.get(chunk_id)
                if current is not None and current[1] <= score:
                    continue

                document = Document(
                    page_content=row["content"],
                    metadata={
                        "chunk_id": chunk_id,
                        "source_key": row["source_key"],
                        "source_path": row["source_path"],
                        "source_name": row["source_name"],
                        "title": row["title"],
                        "author": row["author"],
                        "page": row["page"],
                        "chunk": row["chunk_index"],
                    },
                )
                seen[chunk_id] = (document, score)

    ranked = sorted(seen.values(), key=lambda item: item[1])
    return ranked[:limit]


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    return connection


def _batched(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
