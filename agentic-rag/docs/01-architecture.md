# Architecture Overview

## System Diagram

```mermaid
flowchart TD
    A["🧑 User Query"] --> SEC{"🛡️ Security Scan"}
    SEC -->|DANGER| DENY["🚫 Blocked"]
    SEC -->|SAFE| ROUTE{"🔀 Route Query"}

    ROUTE -->|vectorstore| RET["📥 Retrieve from ChromaDB"]
    ROUTE -->|direct_llm| GEN

    RET --> GRADE["📝 Grade Documents"]
    GRADE -->|all relevant| GEN["🤖 Generate Answer"]
    GRADE -->|some irrelevant| WEB["🌐 DuckDuckGo Fallback"]
    WEB --> GEN

    GEN --> HALL{"🔍 Hallucination Check"}
    HALL -->|grounded| REL{"✅ Answers Question?"}
    HALL -->|not grounded, retry < 3| GEN
    REL -->|yes| OUT["✔️ Return Answer + Sources"]
    REL -->|no| WEB
```

## Layer Boundaries

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Knowledge | `src/knowledge/` | PDF parsing, chunking, versioning, metadata schemas |
| Retrieval | `src/retrieval/` | Embeddings, ChromaDB, retriever factory |
| LLM Interface | `src/llm_interface/` | ChatOllama, prompts, LCEL chains |
| Orchestration | `src/orchestration/` | AgentState, graph nodes, StateGraph wiring |

## Data Flow (Medallion)

```mermaid
flowchart LR
    B["🥉 Bronze\ncorpus/*.pdf"] -->|Docling| S["🥈 Silver\ndata/silver/*.json"]
    S -->|Chunk + Embed| G["🥇 Gold\ndata/gold/chroma/"]
```
