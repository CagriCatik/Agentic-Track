# 07.15 — Documentation Helper in Production

## Overview

In this lesson, we look at **Chat LangChain**, the official, open-source documentation helper built by the LangChain team. This serves as a real-world example of taking our "Documentation Helper" prototype and scaling it into a production-ready application using advanced agentic RAG patterns (specifically, explicit query rewriting and multi-agent coordination via LangGraph).

---

## The Chat LangChain Application

If you go to `chat.langchain.com`, you'll see a UI similar to the Streamlit app we just built. However, its backend architecture is significantly more sophisticated.

### 1. The Query Expansion Flow

If you ask Chat LangChain "What is LangChain?", it doesn't just search the vector store for "What is LangChain?".

Instead, it employs **Query Expansion** (also known as sub-query generation):

```mermaid
flowchart TD
    Q[User Prompt:\n"What is LangChain?"]
    
    Q --> A[Subquery 1:\nReview docs and gather\ncomprehensive definition]
    Q --> B[Subquery 2:\nCore components of\nLangChain]
    Q --> C[Subquery 3:\nUse cases for\nLangChain]

    A --> VS[(Vector Store)]
    B --> VS
    C --> VS

    VS -. "Multiple Docs" .-> RANK[Re-rank and Filter Results]
    RANK --> LLM[Final Generation]

    style VS fill:#10b981,color:#fff
```

**Why do this?**
A single user query is often too vague for effective semantic search. By having an LLM generate 3-5 distinct, specific questions based on the user's prompt, we cast a wider net in the vector store and retrieve higher-quality context.

### 2. Generative UI (Transparency & Trust)

Chat LangChain exposes its internal state directly to the user interface. It shows:
- The sub-queries being generated.
- The parallel searches hitting the vector store.
- The exact documents retrieved before generation begins.

This is the principle of Generative UI introduced in the previous lesson. It builds immense trust by showing the "scratchpad" of the agent's reasoning.

---

## 3. Dissecting the Architecture

Chat LangChain is fully open-source on GitHub (`langchain-ai/chat-langchain`). Let's look at its tech stack:

| Component | Responsibility | Pattern implementation |
|---|---|---|
| **LangChain Core** | Prompts, Embeddings, Vector Store connections | Basic integration |
| **LangGraph** | Multi-Agent Coordination, Flow Control | The core logic engine driving the query routing and aggregation |
| **Next.js + TypeScript** | The frontend | Consuming the streaming state of the LangGraph execution |

### Exploring `prompts.py`

If we check the repository (`backend/chat_langchain/prompts.py`), we find highly specific prompts used throughout the application pipeline:

- **Router Prompt**: Decides if the question requires looking at the codebase or documentation.
- **Generate Queries Prompt**: Takes the user's intent and forces the LLM to write 3 optimal semantic search queries.
- **Answer Prompt**: The final prompt combining all the retrieved context.

### Example: Coreference Resolution

If you ask: *"Who created LangChain?"*
And then follow up with: *"When was it created?"*

The system performs **Coreference Resolution**. It looks at the chat history, understands that "it" refers to LangChain, and automatically rewrites the query to *"When was LangChain created?"* before performing the similarity search. Without this step, searching a vector store for *"When was it created?"* would return useless results.

---

## Summary

The difference between our prototype and a production app lies in the **intermediate steps**.

| Feature | Prototype (Our App) | Production (Chat LangChain) |
|---|---|---|
| **Retrieval** | Single search based on user query | Query Expansion (Sub-queries), Re-ranking |
| **Context** | User prompt directly hits Vector Store | Coreference Resolution (Contextual Rewriting) |
| **Flow Control** | Prebuilt Agent (`create_agent`) | Custom LangGraph State Machine |
| **UI** | Synchronous Streamlit | Streaming Generative UI (Next.js) |
| **Multi-Agent** | No | Yes (Routing between Code vs Docs) |

We will learn how to build architectures identical to `Chat LangChain` natively in the dedicated LangGraph section of the course!