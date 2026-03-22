# 12.02 — Project Setup

## Overview

This lesson covers the project initialization for the Reflexion Agent. The setup is nearly identical to the Reflection Agent (Section 11), with one key addition: the **Tavily API key** for web search.

---

## Step 1: Initialize the Project

```bash
mkdir reflexion-agent
cd reflexion-agent
poetry init    # Accept defaults
```

---

## Step 2: Install Dependencies

```bash
poetry add python-dotenv black isort langchain langchain-openai langgraph langchain-tavily
```

| Package | Purpose |
|---|---|
| `python-dotenv` | Load API keys from `.env` file |
| `black` / `isort` | Code formatting and import sorting |
| `langchain` | Core framework — prompts, output parsers, message types |
| `langchain-openai` | OpenAI integration — `ChatOpenAI` for GPT-4 Turbo |
| `langgraph` | Graph-based workflow orchestration |
| `langchain-tavily` | Tavily search engine integration for real-time web search |

> [!NOTE]
> This project uses **GPT-4 Turbo** instead of GPT-3.5 (used in Section 11). GPT-4's stronger reasoning is needed for: (1) self-critique that's specific enough to act on, (2) reliable function calling with complex Pydantic schemas, and (3) coherent article revision across multiple iterations.

---

## Step 3: Configure Environment Variables

Create a `.env` file:

```bash
# OpenAI (required — LLM for drafting, critiquing, and revising)
OPENAI_API_KEY=sk-your-key-here

# Tavily (required — web search engine)
TAVILY_API_KEY=tvly-your-key-here

# LangSmith (recommended — tracing and observability)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=reflexion-agent
LANGCHAIN_API_KEY=ls-your-key-here
```

| Variable | Why It's Needed |
|---|---|
| `OPENAI_API_KEY` | All LLM calls (first responder, revisor) use GPT-4 Turbo |
| `TAVILY_API_KEY` | The Execute Tools node calls Tavily for real-time web search results |
| `LANGCHAIN_TRACING_V2` | Enables LangSmith tracing — critical for debugging the multi-step agent |
| `LANGCHAIN_PROJECT` | Names the project in LangSmith dashboard |

> [!TIP]
> Get a Tavily API key at [tavily.com](https://tavily.com). Tavily offers a free tier with enough requests for development and testing.

---

## Step 4: Create Boilerplate and Validate

```python
# main.py
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    print("Hello Reflexion!")
```

```bash
python main.py
# Output: Hello Reflexion!
```

---

## Project File Structure

```
reflexion-agent/
├── .env                  ← API keys (not committed)
├── main.py               ← Graph definition, nodes, execution
├── chains.py             ← First responder and revisor chains
├── schemas.py            ← Pydantic models (AnswerQuestion, ReviseAnswer)
├── tool_executor.py      ← Tavily search tool + ToolNode setup
├── pyproject.toml         ← Project configuration
└── poetry.lock            ← Exact dependency versions
```

> [!IMPORTANT]
> Note the increased file count compared to the Reflection Agent (Section 11, which had just `main.py` + `chains.py`). The Reflexion Agent adds `schemas.py` for Pydantic output models and `tool_executor.py` for search tool configuration. This separation keeps each file focused and testable.

---

## Summary

| Step | Action | New vs. Section 11 |
|---|---|---|
| Poetry init | Same as Section 11 | Same |
| Install deps | Added `langchain-tavily` | **New** — for web search |
| API keys | Added `TAVILY_API_KEY` | **New** — for Tavily search engine |
| File structure | 4 Python files instead of 2 | **New** — `schemas.py` + `tool_executor.py` |
| LLM model | GPT-4 Turbo (was GPT-3.5) | **Changed** — needs stronger reasoning |