# Prompt Design

All prompts are centralized in `src/llm_interface/prompts.py`.

## 6 Chains

| Chain | Purpose | Output |
|-------|---------|--------|
| Security | Detects prompt injection | "SAFE" or "DANGER" |
| Router | Adaptive RAG routing | "vectorstore" or "direct_llm" |
| Retrieval Grader | CRAG — grade doc relevance | "yes" or "no" |
| Generator | RAG answer with citations | Free-text + `[Quelle: X, Seite Y]` |
| Hallucination Grader | Self-RAG — check grounding | "yes" or "no" |
| Answer Grader | Self-RAG — check relevance | "yes" or "no" |

## Design Principles

1. **Binary outputs** for grading chains — forces deterministic routing
2. **Citation instruction** embedded in generation prompt — LLM uses metadata
3. **German-aware** router — knows the automotive domain vocabulary
4. **Language-agnostic** responses — answers in the same language as the question
