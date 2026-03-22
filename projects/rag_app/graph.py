"""Grounded LangGraph assembly for a corpus-driven RAG assistant."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, TypedDict

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from .retrieval import RetrievalBundle, bundle_from_documents

NO_ANSWER_EN = "I don't know based on the indexed sources."
NO_ANSWER_DE = "Ich weiss es nicht auf Basis der indexierten Quellen."
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupportAssessment:
    status: str
    confidence: float
    reasons: list[str]


class GraphState(TypedDict, total=False):
    question: str
    history: str
    context: str
    generation: str
    revision_count: int
    docs: list[Any]
    support_status: str
    support_confidence: float
    support_reasons: list[str]


def localize_no_answer(question: str) -> str:
    lowered = question.casefold()
    german_markers = (
        " der ",
        " die ",
        " das ",
        " und ",
        " ist ",
        " wer ",
        " was ",
        " wie ",
        " warum ",
        " nicht ",
        " quellen ",
    )
    padded = f" {lowered} "
    if any(marker in padded for marker in german_markers) or any(char in lowered for char in "äöüß"):
        return NO_ANSWER_DE
    return NO_ANSWER_EN


def assess_support(bundle: RetrievalBundle) -> SupportAssessment:
    if not bundle.hits:
        return SupportAssessment(
            status="unsupported",
            confidence=0.0,
            reasons=["no retrieved documents"],
        )

    top_hits = bundle.hits[:3]
    max_overlap = max(hit.overlap for hit in top_hits)
    avg_overlap = sum(hit.overlap for hit in top_hits) / len(top_hits)
    fused_total = sum(hit.fused_score for hit in top_hits)
    rerank_values = [hit.rerank_score if hit.rerank_score is not None else hit.overlap for hit in top_hits]
    top_rerank = max(rerank_values)
    rerank_margin = 0.0
    if len(top_hits) >= 2:
        ordered_rerank = sorted(rerank_values, reverse=True)
        rerank_margin = ordered_rerank[0] - ordered_rerank[1]
    lexical_hits = sum(1 for hit in top_hits if hit.lexical_rank is not None)
    strong_semantic = any(
        (hit.semantic_score or 0.0) >= 0.8 and hit.overlap >= 0.2 for hit in top_hits
    )
    query_terms = set(bundle.plan.keywords[:8])
    query_terms.update(term.casefold() for term in bundle.plan.uppercase_terms[:4])
    query_term_count = max(1, len(query_terms))
    matched_terms_top = max(
        hit.matched_term_count or round(hit.overlap * query_term_count)
        for hit in top_hits
    )

    confidence = 0.0
    confidence += min(max_overlap / 0.45, 1.0) * 0.55
    confidence += min(avg_overlap / 0.30, 1.0) * 0.15
    confidence += min(fused_total / 0.08, 1.0) * 0.05
    confidence += min(top_rerank / 0.7, 1.0) * 0.20
    confidence += 0.075 if lexical_hits else 0.0
    confidence += 0.075 if strong_semantic else 0.0
    confidence += 0.025 if rerank_margin >= 0.1 else 0.0
    confidence = min(confidence, 1.0)

    reasons = [
        f"max_overlap={max_overlap:.2f}",
        f"avg_overlap={avg_overlap:.2f}",
        f"top3_fused={fused_total:.3f}",
        f"top_rerank={top_rerank:.2f}",
        f"rerank_margin={rerank_margin:.2f}",
        f"top_matched_terms={matched_terms_top}/{query_term_count}",
    ]

    if max_overlap < 0.12 and not strong_semantic:
        return SupportAssessment(
            status="unsupported",
            confidence=min(confidence, 0.3),
            reasons=reasons + ["retrieved text does not overlap enough with the query"],
        )

    if query_term_count >= 2 and matched_terms_top < min(2, query_term_count) and not strong_semantic:
        return SupportAssessment(
            status="unsupported",
            confidence=min(confidence, 0.35),
            reasons=reasons + ["too few subject terms match the top evidence block"],
        )

    if top_rerank < 0.28:
        return SupportAssessment(
            status="unsupported",
            confidence=min(confidence, 0.3),
            reasons=reasons + ["reranker score is too weak for a grounded answer"],
        )

    if confidence >= 0.6 or (top_rerank >= 0.45 and max_overlap >= 0.35 and (lexical_hits or strong_semantic)):
        return SupportAssessment(status="supported", confidence=confidence, reasons=reasons)

    if confidence >= 0.35 or max_overlap >= 0.2:
        return SupportAssessment(
            status="weak",
            confidence=confidence,
            reasons=reasons + ["evidence is partial or weakly aligned"],
        )

    return SupportAssessment(
        status="unsupported",
        confidence=confidence,
        reasons=reasons + ["support threshold not met"],
    )


def _format_context(bundle: RetrievalBundle) -> str:
    blocks: list[str] = []
    for index, hit in enumerate(bundle.hits, start=1):
        metadata = hit.document.metadata or {}
        title = metadata.get("title") or metadata.get("source_name") or "Untitled"
        author = metadata.get("author") or "Unknown"
        source = metadata.get("source_name") or metadata.get("source_path") or "Unknown"
        page = metadata.get("page", "?")
        retrieval_score = metadata.get("retrieval_score", hit.fused_score)
        rerank_score = metadata.get("rerank_score", hit.rerank_score or 0.0)
        blocks.append(
            f"[{index}] Title: {title}\n"
            f"Author: {author}\n"
            f"Source: {source}\n"
            f"Location: {page}\n"
            f"Support: fused={retrieval_score} rerank={rerank_score} overlap={hit.overlap:.2f}\n"
            f"Content:\n{hit.document.page_content.strip()}"
        )
    return "\n\n".join(blocks)


def build_graph(
    *,
    chat_model: str,
    temperature: float,
    system_prompt: str,
    retriever: Any,
    ollama_base_url: str | None = None,
):
    if retriever is None:
        raise ValueError("retriever is required")

    llm = ChatOllama(
        model=chat_model,
        temperature=temperature,
        base_url=ollama_base_url,
    )

    def retrieve_node(state: GraphState) -> GraphState:
        question = state["question"]
        if hasattr(retriever, "search"):
            bundle = retriever.search(question)
        else:
            bundle = bundle_from_documents(question, retriever.invoke(question))
        support = assess_support(bundle)
        logger.info(
            "Retrieved evidence: question=%r hits=%d support_status=%s support_confidence=%.2f reasons=%s",
            question[:200],
            len(bundle.hits),
            support.status,
            support.confidence,
            support.reasons,
        )
        return {
            "context": _format_context(bundle),
            "docs": bundle.documents,
            "support_status": support.status,
            "support_confidence": support.confidence,
            "support_reasons": support.reasons,
            "revision_count": 0,
        }

    def generate_node(state: GraphState) -> GraphState:
        question = state["question"]
        history = state.get("history", "")
        context = state.get("context", "")
        support_status = state.get("support_status", "unsupported")
        support_confidence = float(state.get("support_confidence", 0.0))
        support_reasons = state.get("support_reasons", [])

        if support_status == "unsupported" or not context.strip():
            logger.info(
                "Skipping generation due to unsupported evidence: question=%r support_status=%s",
                question[:200],
                support_status,
            )
            return {
                "generation": localize_no_answer(question),
                "revision_count": 1,
            }

        support_instruction = (
            "The retrieved evidence is weak. Answer conservatively, separate supported facts from missing facts, "
            "and avoid broad conclusions."
            if support_status == "weak"
            else "The retrieved evidence is adequate. Answer directly, but stay grounded in the cited passages."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "human",
                    "Conversation history:\n{history}\n\n"
                    "Question:\n{question}\n\n"
                    "Evidence quality:\n"
                    "status={support_status}\n"
                    "confidence={support_confidence:.2f}\n"
                    "signals={support_reasons}\n\n"
                    "Retrieved source blocks:\n{context}\n\n"
                    "Rules:\n"
                    "1. Use only the retrieved source blocks.\n"
                    "2. If the evidence is partial, say what is supported and what is missing.\n"
                    "3. Cite supporting blocks inline with [1], [2], etc.\n"
                    "4. Match the user's language unless the user explicitly asked for another language.\n"
                    "5. Do not invent facts, citations, metadata, or implications.\n"
                    "6. Adapt length to the question: concise for narrow questions, structured for broad ones.\n\n"
                    "Additional guidance:\n{support_instruction}\n",
                ),
            ]
        )
        chain = prompt | llm
        response = chain.invoke(
            {
                "history": history or "No relevant history.",
                "question": question,
                "support_status": support_status,
                "support_confidence": support_confidence,
                "support_reasons": "; ".join(support_reasons) or "none",
                "context": context,
                "support_instruction": support_instruction,
            }
        )
        output = response.content if hasattr(response, "content") else str(response)
        logger.info(
            "Generated grounded answer: question=%r support_status=%s support_confidence=%.2f output_chars=%d",
            question[:200],
            support_status,
            support_confidence,
            len(output.strip()),
        )
        return {
            "generation": output.strip() or localize_no_answer(question),
            "revision_count": 1,
        }

    workflow = StateGraph(GraphState)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()
