<div align="center">

# Agentic Track - Automotive RAG & Knowledge Base

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-green)](#)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20RAG-orange)](#)
[![ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB-purple)](#)
[![Docs](https://img.shields.io/badge/Docs-MkDocs-informational)](#)
[![License](https://img.shields.io/badge/License-Add%20Your%20License-lightgrey)](#)

**A project hub for production-oriented Generative AI workflows focused on high-precision Agentic RAG for the German automotive engineering domain.**

</div>

---

## Overview

This repository combines document ingestion, structured data processing, retrieval pipelines, and an agent-based reasoning workflow into a single knowledge platform.

It is designed for:
- processing automotive engineering PDFs and technical documents,
- organizing extracted content with a Medallion-style data architecture,
- serving high-quality retrieval with a vector database,
- and running a self-correcting LangGraph workflow for reliable answers.

---

## Repository Structure

| Directory | Purpose |
|---|---|
| [`agentic-rag/`](./agentic-rag/) | Core application code, including the LangGraph agent, FastAPI server, CLI, and Medallion pipeline logic. |
| [`corpus/`](./corpus/) | Source knowledge base containing automotive engineering PDFs and related documents. |
| [`docs/`](./docs/) | MkDocs source files for the technical documentation site. |
| [`tests/`](./agentic-rag/tests/) | Unit, integration, and evaluation test suites. |
| [`tutorials/`](./tutorials/) | Learning materials and framework-specific guides. |

---

## Key Features

### Agentic RAG Workflow
The system implements a corrective and adaptive retrieval pipeline using LangGraph.

Main components include:
- **Security layer** to reduce prompt injection and jailbreak risks,
- **Routing logic** to choose between vector retrieval, direct LLM answering, or web search,
- **Document grading** to check whether retrieved content is relevant,
- **Answer validation and retry logic** to reduce hallucinations and improve output quality.

### Medallion Data Architecture
Data is processed into separate layers under `agentic-rag/data/`:

- **Bronze**: Raw extracted content from source documents  
  - PDF extraction with `pymupdf4llm`
  - HTML conversion with `MarkItDown`

- **Silver**: Cleaned and normalized records  
  - section headers
  - metadata enrichment
  - page-level traceability

- **Gold**: Retrieval-ready assets  
  - chunked documents
  - optimized embeddings
  - ChromaDB vector index

---

## Quick Start

Make sure the following tools are installed:
- [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.com/)

### 1. Set up the environment

```powershell
cd agentic-rag
uv sync
ollama pull llama3:8b
ollama pull nomic-embed-text
````

### 2. Ingest documents

Process local PDFs and documentation content into the vector store:

```powershell
uv run python app/cli.py --ingest
```

### 3. Start the interactive application

```powershell
uv run python app/cli.py
```

---

## Configuration

Project behavior can be adjusted through:

```text
agentic-rag/config.yaml
```

Recommended starting points:

* **Model selection**: `gpt-oss:120b-cloud` for strong German-language synthesis quality
* **Retrieval depth**: `top_k: 6+` for improved recall before relevance filtering
* **Hallucination grading**: useful for safer responses, but may increase latency during local testing

---

## Typical Workflow

1. Add source documents to the corpus.
2. Run the ingestion pipeline.
3. Build or refresh the vector store.
4. Query the system through the CLI or API.
5. Let the LangGraph workflow retrieve, grade, validate, and refine responses.

---

## Documentation

Technical documentation lives in the [`docs/`](./docs/) directory and can be used to build a full MkDocs site for project references, architecture notes, and usage guides.

---

## Testing

Tests are located in:

```text
agentic-rag/tests/
```

They cover:

* unit tests,
* integration tests,
* and evaluation workflows for retrieval and answer quality.

---

## Use Cases

This repository is suitable for:

* automotive engineering knowledge bases,
* technical PDF question-answering systems,
* domain-specific RAG assistants,
* internal documentation search,
* and agent-based retrieval pipelines that require validation and correction steps.

---

## Notes

This repository is structured to support both experimentation and production-oriented iteration. The main emphasis is on traceable ingestion, retrieval quality, and reliable answer generation in specialized technical domains.