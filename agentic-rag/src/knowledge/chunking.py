"""Silver → Gold: Split documents into retrieval-ready chunks with inherited metadata."""

from __future__ import annotations

import hashlib

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import get_settings


def chunk_documents(documents: list[Document]) -> list[Document]:
    """Split documents into smaller chunks, preserving citation metadata.

    Each resulting chunk inherits the metadata from its parent document
    (source_file, page_start, page_end, section_header).
    """
    settings = get_settings()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.ingestion.chunk_size,
        chunk_overlap=settings.ingestion.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Document] = []
    chunk_index = 0

    for doc in documents:
        splits = splitter.split_text(doc.page_content)

        for split_text in splits:
            if not split_text.strip():
                continue

            # Inherit ALL metadata from parent document
            inherited_metadata = dict(doc.metadata)
            inherited_metadata["chunk_index"] = chunk_index
            inherited_metadata["chunk_hash"] = hashlib.sha256(
                split_text.encode("utf-8")
            ).hexdigest()[:16]

            chunks.append(
                Document(page_content=split_text, metadata=inherited_metadata)
            )
            chunk_index += 1

    return chunks
