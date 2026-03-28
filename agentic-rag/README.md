# Agentic RAG - Automotive Engineering Knowledge Base

[![Architecture: LangGraph](https://img.shields.io/badge/Architecture-LangGraph-blue)](https://github.com/langchain-ai/langgraph)
[![Data: Medallion](https://img.shields.io/badge/Data-Medallion-orange)](https://www.databricks.com/glossary/medallion-architecture)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)

A production-grade, fully local **Agentic RAG** system designed for high-fidelity Q&A over German automotive engineering documentation. This system uses a strict **Medallion Architecture** to ensure data provenance and a sophisticated **LangGraph** state machine to minimize hallucinations and maximize retrieval relevance.

---

## Architecture

### 1. Data Pipeline (Medallion Tier)
Unlike standard RAG systems that treat the vector store as the source of truth, this project implements a 4-stage pipeline to ensure 100% deterministic rebuilds and accurate page-level citations:

*   🥉 **Bronze**: Raw ingestion artifacts. Stores the original PDF/Markdown and raw extraction results (`pymupdf4llm`).
*   🥈 **Silver**: Normalized, structured records. Extracts section headers, tables, and figures while preserving PDF page numbering.
*   🥇 **Gold**: Canonical retrieval chunks. Vendor-neutral JSON chunks with rich metadata and parent-child lineage.
*   🔗 **Index Layer**: Ephemeral ChromaDB serving layer, fully rebuildable from the Gold tier.

### 2. Orchestration (Agentic Graph)
The retrieval logic is a state-managed graph that includes:
*   **Security Gateway**: Detects and blocks prompt injection or jailbreak attempts.
*   **Correction Loop**: If retrieved chunks are graded as irrelevant, the agent triggers a web search (Tavily) as a fallback.
*   **Self-Correction**: Validates the final answer against the retrieved context to eliminate hallucinations.
*   **Adaptive Routing**: Intelligent routing between local vector stores and direct-to-web search based on query intent.

---

## Quick Start

### Prerequisites
*   [uv](https://github.com/astral-sh/uv) (Python package manager)
*   [Ollama](https://ollama.com/) (for local LLMs)
*   [Docker](https://www.docker.com/) (optional, for containerized deployments)

### Setup
1.  **Sync Environment**:
    ```powershell
    uv sync
    ```
2.  **Pull Models**:
    ```powershell
    ollama pull llama3:8b
    ollama pull nomic-embed-text
    ```
3.  **Run Ingestion**:
    Place your PDFs in the `corpus/` directory and run:
    ```powershell
    uv run python app/cli.py --ingest --force
    ```

### Execution
*   **CLI Mode**: `uv run python app/cli.py`
*   **API Server**: `uv run python app/api.py` (OpenAI-compatible endpoints)
*   **Evaluation**: `uv run python evaluation/runner.py --dataset tests/evaluation/eval_dataset.json`

---

## Configuration

Control the entire system via `config.yaml`. No code changes required to toggle performance vs. accuracy:

```yaml
orchestration:
  security_enabled: true           # Enable/disable injection detection
  document_grading_enabled: true   # LLM-as-a-judge for retrieval
  web_search_enabled: true         # Fallback to internet if RAG fails
  hallucination_grading_enabled: true
```

---

## Evaluation & Validation

The system includes a dedicated evaluation suite using **LLM-as-a-Judge** to measure:
1.  **Faithfulness**: Does the answer only use the provided context?
2.  **Relevance**: Does the answer actually address the user's question?
3.  **Citation Accuracy**: Does the page number in the citation match the source PDF?

Detailed reports are generated in `evaluation/reports/` with JSON and Markdown summaries.

---

## Stack
- **LangChain / LangGraph**: Orchestration & State Management
- **ChromaDB**: Core Vector Database
- **PyMuPDF4LLM**: High-fidelity PDF-to-Markdown extraction
- **FastAPI**: OpenAI-compatible streaming API
- **uv**: Lightning-fast dependency management

---

## Performance Note

- The "Agentic" nature of this graph involves multiple sequential LLM calls (Security -> Router -> Grader -> Answerer -> Hallucination Check). 
- On local hardware (RAG on GPU), end-to-end latency reflects these guardrails. 
- Use `config.yaml` to disable non-essential nodes for faster responses in production.
