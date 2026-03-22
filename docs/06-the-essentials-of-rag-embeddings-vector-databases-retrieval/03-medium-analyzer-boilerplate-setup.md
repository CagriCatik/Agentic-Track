# 06.03 — Medium Analyzer: Boilerplate Setup

## Overview

This lesson sets up the development environment for the **Medium Analyzer** project — a complete RAG pipeline that ingests a Medium blog article about vector databases, stores it in Pinecone, and enables question-answering over it. We cover repository setup, dependency installation, Pinecone index creation, and environment variable configuration.

---

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd langchain-course
git checkout -b project/rag-gist <initial-commit-hash>
```

---

## Step 2: Install Dependencies

```bash
uv lock   # Resolve dependencies from pyproject.toml
uv sync   # Install everything into .venv
```

### Dependency Table

| Package | Purpose |
|---|---|
| `langchain` | Core framework — prompts, chains, LCEL |
| `langchain-community` | Community loaders (e.g., `TextLoader`) |
| `langchain-openai` | OpenAI integration — `ChatOpenAI` + `OpenAIEmbeddings` |
| `langchain-pinecone` | Pinecone vector store integration |
| `python-dotenv` | Load API keys from `.env` file |
| `black` / `isort` | Code formatting |

> [!TIP]
> The project uses **uv** as the package manager (fast Rust-based alternative to pip/poetry). `uv lock` generates a lock file from `pyproject.toml`, and `uv sync` installs everything into a virtual environment at `.venv/`.

---

## Step 3: Configure the IDE

After `uv sync` creates the `.venv/` directory, configure your IDE to use that interpreter:

1. Inside the terminal (with venv active): `which python3` → copy the path
2. In VS Code / Cursor: `Ctrl+Shift+P` → "Python: Select Interpreter" → paste the path

This resolves import errors in the editor.

---

## Step 4: Create a Pinecone Index

### What Is Pinecone?

Pinecone is a **managed cloud vector database**. You don't install or maintain anything — Pinecone handles storage, indexing, and similarity search infrastructure. It has a **free tier** that's sufficient for development.

### Creating the Index

1. Go to [pinecone.io](https://pinecone.io) → Log in
2. Click **Create Index**
3. Configure:

| Setting | Value | Why |
|---|---|---|
| **Index name** | `medium-blogs-embeddings-index` | Descriptive; matches the `.env` variable |
| **Dimensions** | `1536` | Matches `text-embedding-3-small` output at full dimensionality |
| **Metric** | `cosine` | Standard for text similarity |
| **Type** | `Dense` | Standard embedding vectors (not sparse keyword vectors) |
| **Capacity** | `Serverless` | Scales automatically; free tier friendly |
| **Cloud / Region** | `AWS us-east-1` (default) | Choose the region closest to your application |

### Vector Dimensionality

The dimension (1536) **must match** the output dimensionality of the embedding model:

| Embedding Model | Default Dimensions | Settable |
|---|---|---|
| `text-embedding-3-small` | 512 (default), up to 1536 | ✅ Yes |
| `text-embedding-3-large` | 256 (default), up to 3072 | ✅ Yes |
| `text-embedding-ada-002` | 1536 (fixed) | ❌ No |

> [!IMPORTANT]
> Longer vectors hold more semantic information but cost more storage. The dimension of the index and the embedding model **must match exactly** — a mismatch causes an error on insertion.

### Similarity Metrics

| Metric | What It Measures | When to Use |
|---|---|---|
| **Cosine** | Angle between vectors (direction) | Text similarity — **default choice** |
| **Euclidean** | Geometric distance | When vector magnitude is meaningful |
| **Dot product** | Magnitude × direction | Fast; good for normalized vectors |

### Production Considerations

- **Cloud provider**: Pinecone supports AWS, GCP, Azure. Choose based on compliance/privacy needs.
- **Region**: Deploy the vector store in the **same region** as your RAG application to avoid cross-region latency (egress costs).
- **Capacity mode**: Serverless is fine for development. Dedicated pods give predictable latency for production.

---

## Step 5: Configure Environment Variables

Create a `.env` file:

```bash
# OpenAI (LLM + Embeddings)
OPENAI_API_KEY=sk-your-key-here

# Pinecone (Vector Store)
PINECONE_API_KEY=pcsk-your-key-here
INDEX_NAME=medium-blogs-embeddings-index

# LangSmith (Tracing - recommended)
LANGSMITH_API_KEY=ls-your-key-here
LANGSMITH_PROJECT=rag-gist
LANGSMITH_TRACING=true
```

| Variable | Why It's Needed |
|---|---|
| `OPENAI_API_KEY` | LLM calls (GPT-3.5/4) + Embedding API calls |
| `PINECONE_API_KEY` | Authentication for vector store operations |
| `INDEX_NAME` | Which Pinecone index to read from / write to |
| `LANGSMITH_*` | Tracing — see every step of the RAG pipeline in the LangSmith UI |

> [!WARNING]
> The `PINECONE_API_KEY` variable name is important — `langchain-pinecone` expects this **exact** name when auto-detecting the API key from environment variables.

---

## Step 6: Validate the Setup

```python
# ingestion.py
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("Ingestion...")
    print(os.environ["PINECONE_API_KEY"][:8] + "...")   # Quick check
```

Run: `python ingestion.py` → should print the first 8 characters of your Pinecone key.

---

## Project File Structure

```
langchain-course/
├── .env                  ← API keys (gitignored)
├── .gitignore            ← Excludes .env, .venv
├── .python-version       ← Python version constraint
├── pyproject.toml        ← Dependencies
├── uv.lock               ← Exact dependency versions
├── ingestion.py          ← Ingestion pipeline (load → split → embed → store)
├── main.py               ← Retrieval pipeline (query → search → augment → generate)
└── mediumblog.txt        ← Source document (Medium article about vector databases)
```

---

## Summary

| Step | What We Did | Key Decision |
|---|---|---|
| Clone repo | Set up the starter code | Branch `project/rag-gist` |
| Install deps | `uv lock && uv sync` | Latest LangChain versions |
| Configure IDE | Point to `.venv` Python interpreter | Resolves import errors |
| Create Pinecone index | 1536 dimensions, cosine metric, serverless | Matches `text-embedding-3-small` output |
| Environment variables | OpenAI, Pinecone, LangSmith keys | `PINECONE_API_KEY` must be exact name |
| Validate | Run `ingestion.py` → prints key prefix | Confirms setup works |