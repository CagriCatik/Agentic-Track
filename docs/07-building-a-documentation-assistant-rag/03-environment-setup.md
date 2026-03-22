# 07.03 — Environment Setup

## Overview

This lesson sets up the development environment for the Documentation Helper project — cloning the repository, installing dependencies, creating a Pinecone index, and configuring all required API keys and environment variables.

---

## Step 1: Clone the Repository

```bash
git clone <repository-url> -b 1-start-here
cd langchain-course
```

The `-b 1-start-here` flag checks out the starting branch with all boilerplate code pre-configured.

---

## Step 2: Create the Pinecone Index

Navigate to [pinecone.io](https://pinecone.io) and create a new index:

| Setting | Value | Why |
|---|---|---|
| **Index name** | `langchain-doc-index` | Descriptive; matches `.env` variable |
| **Embedding model** | `text-embedding-3-small` (OpenAI) | Select from the model dropdown |
| **Dimensions** | `1536` | Full dimensionality for maximum semantic information |
| **Metric** | `cosine` | Standard for text similarity |
| **Capacity** | `Serverless` | Scales automatically; free tier friendly |
| **Cloud / Region** | AWS us-east-1 (default) | Choose based on latency and compliance |

### Production Considerations

| Factor | What to Consider |
|---|---|
| **Cloud provider** | Choose AWS, GCP, or Azure to match your existing infrastructure |
| **Region** | Deploy in the same region as your application to minimize latency |
| **GDPR** | For EU compliance, select a European data center region |
| **Latency** | Co-locate vector store with your RAG application to avoid cross-region egress costs |

---

## Step 3: Configure Environment Variables

Create a `.env` file (gitignored — never commit secrets):

```bash
# LLM + Embeddings
OPENAI_API_KEY=sk-your-key-here

# Vector Store
PINECONE_API_KEY=pcsk-your-key-here
INDEX_NAME=langchain-doc-index

# Tracing (recommended)
LANGSMITH_API_KEY=ls-your-key-here
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=documentation-helper

# Web Crawling
TAVILY_API_KEY=tvly-your-key-here
```

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Embedding API + LLM inference |
| `PINECONE_API_KEY` | Vector store authentication |
| `INDEX_NAME` | Which Pinecone index to use |
| `LANGSMITH_*` | Tracing every step of the pipeline in LangSmith |
| `TAVILY_API_KEY` | Web crawling and content extraction |

---

## Step 4: Install Dependencies

```bash
# Using Pipenv (as shown in this section's videos)
pipenv install

# Using uv (modern alternative — recommended)
uv sync
```

### Key Dependencies

| Package | Purpose |
|---|---|
| `langchain` | Core framework — chains, prompts, LCEL |
| `langchain-community` | Community document loaders |
| `langchain-openai` | OpenAI embeddings + chat models |
| `langchain-pinecone` | Pinecone vector store integration |
| `langchain-tavily` | Tavily crawling integration (TavilyCrawl, TavilyMap, TavilyExtract) |
| `streamlit` | Frontend chat UI |
| `python-dotenv` | Load `.env` file |
| `certifi` | SSL certificates for HTTP requests |

---

## Step 5: Validate the Setup

```python
# ingestion.py (boilerplate)
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("Ingestion...")
    print(os.environ["PINECONE_API_KEY"][:8] + "...")
```

Run: `python ingestion.py` → should print the key prefix without errors.

---

## Project Structure

```
langchain-course/
├── .env                  ← API keys (gitignored)
├── .gitignore
├── Pipfile / pyproject.toml  ← Dependencies
├── Pipfile.lock / uv.lock    ← Locked versions
├── ingestion.py          ← Ingestion pipeline (crawl → chunk → embed → store)
├── main.py               ← Streamlit frontend
├── logger.py             ← Color-coded logging utilities
├── backend/
│   ├── __init__.py
│   └── core.py           ← Retrieval agent implementation
└── docs/                 ← (created during ingestion)
```

---

## Summary

| Step | What We Did |
|---|---|
| Clone repo | Starting branch with boilerplate code |
| Pinecone index | 1536-dim, cosine, serverless |
| `.env` file | OpenAI, Pinecone, LangSmith, Tavily API keys |
| Install deps | `pipenv install` or `uv sync` |
| Validate | Run `ingestion.py` → confirm env vars load |