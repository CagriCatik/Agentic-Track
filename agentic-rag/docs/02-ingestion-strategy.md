# Ingestion Strategy

## Medallion Architecture

| Layer | Directory | Contents | Trigger |
|-------|-----------|----------|---------|
| Bronze | `corpus/` | Raw untouched PDFs | Source of truth — never modified |
| Silver | `data/silver/` | Docling Markdown + page metadata (JSON) | PDF hash changes |
| Gold | `data/gold/chroma/` | Embedded vectors + citation metadata | Silver changes or config changes |

## PDF Parsing (Bronze → Silver)

**Parser**: Docling (IBM) with DocLayNet AI-powered layout analysis.

Key capabilities:
- Table structure recognition (TableFormer)
- Multi-column layout handling
- Page-level provenance tracking (critical for citations)
- Built-in OCR for scanned documents

Each text block extracted by Docling carries `page_number` metadata from the `DocItem.prov` provenance chain.

## Chunking (Silver → Gold)

**Strategy**: `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=200)

Separators (in priority order): `\n\n`, `\n`, `. `, ` `, ``

Each chunk **inherits** all metadata from its parent Silver document:
- `source_file` — which PDF
- `page_start` / `page_end` — which pages
- `section_header` — nearest heading
- `chunk_hash` — SHA-256 for dedup

## Versioning

File-level SHA-256 hashing tracked in `data/manifests/manifest.json`.
- On re-run, only new/changed PDFs are re-parsed (Silver)
- Gold is rebuilt from all Silver data to ensure consistency
