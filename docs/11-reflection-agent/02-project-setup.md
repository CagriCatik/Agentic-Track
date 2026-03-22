# 11.02 — Project Setup

## Overview

This lesson covers the **project initialization** for the Reflection Agent — creating the project directory, installing dependencies, configuring API keys, and validating that everything works before writing any agent logic.

---

## Step 1: Initialize the Project with Poetry

```bash
# Create and navigate to the project directory
mkdir reflection-agent
cd reflection-agent

# Initialize Poetry (accept defaults)
poetry init
```

This generates a `pyproject.toml` file — the project's manifest that tracks all dependencies and their versions.

**Why Poetry?** Poetry provides two key advantages:
1. **Deterministic builds** — the `poetry.lock` file captures exact dependency versions, ensuring every developer gets the same environment
2. **Virtual environment isolation** — Poetry automatically creates and manages a virtual environment, preventing conflicts with other Python projects

---

## Step 2: Install Dependencies

```bash
poetry add python-dotenv black isort langchain langchain-openai langgraph
```

| Package | Purpose |
|---|---|
| `python-dotenv` | Load environment variables from `.env` file — keeps API keys out of source code |
| `black` | Python code formatter — consistent code style |
| `isort` | Import sorter — organizes imports alphabetically and by type |
| `langchain` | Core LLM framework — provides prompt templates, chains, message types |
| `langchain-openai` | OpenAI integration for LangChain — `ChatOpenAI` wrapper for GPT models |
| `langgraph` | Graph-based workflow orchestration — the engine for our generate ↔ reflect loop |

> [!NOTE]
> This project uses **GPT-3.5 Turbo** as the default model (via `ChatOpenAI()`). GPT-3.5 is sufficient for this use case because both the generation and reflection tasks are well within its capabilities, and it's significantly cheaper than GPT-4 for iterative workflows that make multiple LLM calls.

---

## Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-your-key-here

# LangSmith Tracing (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=reflection-agent
LANGCHAIN_API_KEY=ls-your-key-here
```

**What each variable does:**

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Authenticates with OpenAI's API for all LLM calls (both generation and reflection chains) |
| `LANGCHAIN_TRACING_V2=true` | Enables LangSmith tracing — every LLM call, chain invocation, and graph step is logged for debugging |
| `LANGCHAIN_PROJECT` | Names the tracing project in LangSmith — all traces appear under "reflection-agent" |
| `LANGCHAIN_API_KEY` | Authenticates with LangSmith for trace storage |

> [!WARNING]
> **Never commit `.env` to version control.** Add it to your `.gitignore` file. API keys in a public repository are a security risk — they can be scraped and abused within minutes.

---

## Step 4: Create the Main File and Validate

Create `main.py` with the boilerplate:

```python
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("Hello LangGraph!")
```

**Run the sanity check:**

```bash
python main.py
# Output: Hello LangGraph!
```

This validates that:
- ✅ Python can find and import all dependencies
- ✅ The virtual environment is correctly configured
- ✅ The `.env` file is loaded (environment variables are accessible)

### Validating Environment Variables

To confirm your API keys are loaded correctly, you can verify in a Python debugger or a quick script:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Check that the key is loaded (should print a value, not None)
assert os.environ.get("OPENAI_API_KEY") is not None, "OPENAI_API_KEY not set!"
print("✅ All environment variables loaded successfully")
```

---

## Project File Structure

After setup, your project should look like:

```
reflection-agent/
├── .env                  ← API keys (not committed)
├── main.py               ← Entry point — graph definition and execution
├── chains.py             ← Generation and reflection chains (created in lesson 03)
├── pyproject.toml        ← Project configuration and dependencies
└── poetry.lock           ← Exact dependency versions (auto-generated)
```

> [!TIP]
> Note how simple this project is — just **two Python files** (`main.py` and `chains.py`). The Reflection Agent is one of the simplest LangGraph projects, making it an excellent introduction to graph-based workflows. The Agentic RAG project (Section 13) will have a more complex structure with separate directories for nodes, chains, and the graph.

---

## Package Version Reference

At the time of this course, the key packages were at these versions:

| Package | Version |
|---|---|
| `langchain` | 0.1.16 |
| `langgraph` | 0.0.38+ (updated to 1.0 in refilmed version) |

> [!NOTE]
> LangGraph has evolved significantly. The refilmed version of this course uses **LangGraph 1.0**, which introduced some API changes. The core concepts remain the same, but some method names and import paths may differ from earlier versions.

---

## Summary

| Step | Action | Validation |
|---|---|---|
| 1 | Initialize Poetry project | `pyproject.toml` exists |
| 2 | Install 6 dependencies | `poetry.lock` generated, no errors |
| 3 | Create `.env` with API keys | Variables are accessible via `os.environ` |
| 4 | Create `main.py` with boilerplate | `python main.py` prints "Hello LangGraph!" |