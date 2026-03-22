"""Pluggable rerankers for hybrid retrieval candidates."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.documents import Document
from langchain_ollama import ChatOllama

from .retrieval import QueryPlan, RankedDocument, RetrievalBundle, extract_keywords

RERANKER_MODES = frozenset({"feature", "llm", "auto"})


@dataclass(frozen=True)
class RerankerConfig:
    enabled: bool = True
    candidate_limit: int = 24
    mode: str = "auto"
    llm_top_n: int = 8
    llm_weight: float = 0.65
    llm_max_document_chars: int = 1200


@dataclass(frozen=True)
class RerankFeatures:
    rerank_score: float
    matched_terms: tuple[str, ...]
    matched_term_count: int
    title_overlap: float
    exact_phrase_hits: int
    acronym_hits: int
    exact_title_match: bool
    exact_source_match: bool


@dataclass(frozen=True)
class LLMRanking:
    candidate: int
    score: float
    reason: str


class SupportsInvoke(Protocol):
    def invoke(self, input: Any, config: dict[str, Any] | None = None) -> Any:
        ...


class FeatureReranker:
    def __init__(self, *, config: RerankerConfig | None = None) -> None:
        self.config = config or RerankerConfig()

    def rerank(self, bundle: RetrievalBundle) -> RetrievalBundle:
        if not self.config.enabled or not bundle.hits:
            return bundle

        reranked = [self._decorate_hit(bundle.plan, hit) for hit in bundle.hits[: self.config.candidate_limit]]
        reranked.sort(
            key=lambda item: (item.rerank_score or 0.0, item.overlap, item.fused_score),
            reverse=True,
        )
        return RetrievalBundle(
            query=bundle.query,
            plan=bundle.plan,
            hits=reranked + bundle.hits[self.config.candidate_limit :],
        )

    def _decorate_hit(self, plan: QueryPlan, hit: RankedDocument) -> RankedDocument:
        features = score_document(plan, hit.document, hit=hit)
        metadata = dict(hit.document.metadata or {})
        metadata["feature_rerank_score"] = round(features.rerank_score, 6)
        metadata["rerank_score"] = round(features.rerank_score, 6)
        metadata["matched_terms"] = list(features.matched_terms)
        metadata["matched_term_count"] = features.matched_term_count
        metadata["title_overlap"] = round(features.title_overlap, 6)
        metadata["exact_phrase_hits"] = features.exact_phrase_hits
        metadata["acronym_hits"] = features.acronym_hits
        metadata["exact_title_match"] = int(features.exact_title_match)
        metadata["exact_source_match"] = int(features.exact_source_match)
        return _copy_hit(
            hit,
            document=Document(page_content=hit.document.page_content, metadata=metadata),
            rerank_score=features.rerank_score,
            matched_terms=features.matched_terms,
            matched_term_count=features.matched_term_count,
            title_overlap=features.title_overlap,
            exact_phrase_hits=features.exact_phrase_hits,
            acronym_hits=features.acronym_hits,
            exact_title_match=features.exact_title_match,
            exact_source_match=features.exact_source_match,
        )


class PipelineReranker:
    """Feature reranking with an optional LLM refinement stage."""

    def __init__(
        self,
        *,
        config: RerankerConfig | None = None,
        judge: SupportsInvoke | None = None,
    ) -> None:
        self.config = config or RerankerConfig()
        self.feature_reranker = FeatureReranker(config=self.config)
        self.judge = judge

    def rerank(self, bundle: RetrievalBundle) -> RetrievalBundle:
        if not self.config.enabled or not bundle.hits:
            return bundle

        reranked = self.feature_reranker.rerank(bundle)
        if self.config.mode == "feature" or self.judge is None:
            return reranked
        return self._rerank_with_llm(reranked)

    def _rerank_with_llm(self, bundle: RetrievalBundle) -> RetrievalBundle:
        top_n = min(len(bundle.hits), self.config.candidate_limit, self.config.llm_top_n)
        if top_n <= 1:
            return bundle

        candidate_hits = bundle.hits[:top_n]
        prompt = _build_llm_prompt(
            bundle.query,
            bundle.plan,
            candidate_hits,
            max_document_chars=self.config.llm_max_document_chars,
        )
        try:
            response = self.judge.invoke(prompt)
        except Exception:
            return bundle

        content = response.content if hasattr(response, "content") else str(response)
        rankings = _parse_llm_rankings(content, candidate_count=top_n)
        if not rankings:
            return bundle

        ranking_by_candidate = {item.candidate: item for item in rankings}
        llm_hits: list[RankedDocument] = []
        for index, hit in enumerate(candidate_hits, start=1):
            llm_ranking = ranking_by_candidate.get(index)
            if llm_ranking is None:
                llm_hits.append(hit)
                continue

            metadata = dict(hit.document.metadata or {})
            feature_score = float(metadata.get("feature_rerank_score", hit.rerank_score or 0.0))
            combined_score = ((1.0 - self.config.llm_weight) * feature_score) + (
                self.config.llm_weight * llm_ranking.score
            )
            metadata["feature_rerank_score"] = round(feature_score, 6)
            metadata["llm_rerank_score"] = round(llm_ranking.score, 6)
            metadata["llm_rerank_reason"] = llm_ranking.reason
            metadata["rerank_score"] = round(combined_score, 6)

            llm_hits.append(
                _copy_hit(
                    hit,
                    document=Document(page_content=hit.document.page_content, metadata=metadata),
                    rerank_score=combined_score,
                )
            )

        llm_hits.sort(
            key=lambda item: (item.rerank_score or 0.0, item.overlap, item.fused_score),
            reverse=True,
        )
        return RetrievalBundle(
            query=bundle.query,
            plan=bundle.plan,
            hits=llm_hits + bundle.hits[top_n:],
        )


def build_reranker(
    *,
    enabled: bool,
    mode: str,
    candidate_limit: int,
    ollama_base_url: str | None,
    llm_model: str | None = None,
    llm_top_n: int = 8,
    llm_weight: float = 0.65,
    llm_max_document_chars: int = 1200,
) -> PipelineReranker:
    normalized_mode = (mode or "auto").strip().lower()
    if normalized_mode not in RERANKER_MODES:
        raise ValueError(f"Unsupported reranker mode: {mode!r}")

    config = RerankerConfig(
        enabled=enabled,
        candidate_limit=candidate_limit,
        mode=normalized_mode,
        llm_top_n=max(1, min(llm_top_n, candidate_limit)),
        llm_weight=min(max(llm_weight, 0.0), 1.0),
        llm_max_document_chars=max(200, llm_max_document_chars),
    )

    judge: SupportsInvoke | None = None
    if enabled and normalized_mode in {"auto", "llm"} and llm_model:
        judge = ChatOllama(
            model=llm_model,
            temperature=0.0,
            base_url=ollama_base_url,
        )

    return PipelineReranker(config=config, judge=judge)


def score_document(plan: QueryPlan, document: Document, *, hit: RankedDocument | None = None) -> RerankFeatures:
    metadata = document.metadata or {}
    title_text = " ".join(
        part
        for part in [
            str(metadata.get("title", "")),
            str(metadata.get("source_name", "")),
            str(metadata.get("author", "")),
        ]
        if part
    )
    content_text = document.page_content or ""

    query_terms = set(plan.keywords[:8])
    query_terms.update(term.casefold() for term in plan.uppercase_terms[:4])
    if not query_terms:
        query_terms = set(extract_keywords(plan.raw_query, keep_stopwords=True)[:8])

    title_terms = set(extract_keywords(title_text, keep_stopwords=True))
    content_terms = set(extract_keywords(content_text[:1600], keep_stopwords=True))
    all_terms = title_terms | content_terms

    matched_terms = tuple(sorted(term for term in query_terms if term in all_terms))
    matched_term_count = len(matched_terms)
    term_denominator = max(1, len(query_terms))
    overlap = matched_term_count / term_denominator
    title_overlap = len([term for term in query_terms if term in title_terms]) / term_denominator if query_terms else 0.0

    normalized_query = _normalize(plan.raw_query)
    normalized_title = _normalize(title_text)
    normalized_source = _normalize(str(metadata.get("source_name", "")))
    exact_title_match = bool(normalized_query and normalized_title and normalized_query in normalized_title)
    exact_source_match = bool(normalized_query and normalized_source and normalized_source in normalized_query)

    exact_phrase_hits = 0
    phrases = list(plan.quoted_phrases)
    if not phrases and len(plan.keywords) >= 2:
        phrases.append(" ".join(plan.keywords[: min(4, len(plan.keywords))]))
    normalized_body = _normalize(f"{title_text} {content_text[:2000]}")
    for phrase in phrases[:3]:
        normalized_phrase = _normalize(phrase)
        if normalized_phrase and normalized_phrase in normalized_body:
            exact_phrase_hits += 1

    acronym_hits = 0
    upper_body = f" {title_text} {content_text[:1000]} "
    for acronym in plan.uppercase_terms[:4]:
        if re.search(rf"\b{re.escape(acronym)}\b", upper_body):
            acronym_hits += 1

    lexical_signal = 0.0
    semantic_signal = 0.0
    base_signal = 0.0
    if hit is not None:
        if hit.lexical_rank is not None:
            lexical_signal = 1.0 / (1 + hit.lexical_rank)
        if hit.semantic_score is not None:
            semantic_signal = hit.semantic_score if overlap >= 0.15 or title_overlap >= 0.15 else min(hit.semantic_score, 0.2)
        base_signal = min(hit.fused_score / 0.08, 1.0)

    rerank_score = 0.0
    rerank_score += overlap * 0.42
    rerank_score += title_overlap * 0.18
    rerank_score += min(exact_phrase_hits, 2) * 0.10
    rerank_score += min(acronym_hits, 2) * 0.08
    rerank_score += 0.08 if exact_title_match else 0.0
    rerank_score += 0.14 if exact_source_match else 0.0
    rerank_score += lexical_signal * 0.07
    rerank_score += semantic_signal * 0.05
    rerank_score += base_signal * 0.02
    rerank_score = min(rerank_score, 1.0)

    return RerankFeatures(
        rerank_score=rerank_score,
        matched_terms=matched_terms,
        matched_term_count=matched_term_count,
        title_overlap=title_overlap,
        exact_phrase_hits=exact_phrase_hits,
        acronym_hits=acronym_hits,
        exact_title_match=exact_title_match,
        exact_source_match=exact_source_match,
    )


def _build_llm_prompt(
    question: str,
    plan: QueryPlan,
    hits: list[RankedDocument],
    *,
    max_document_chars: int,
) -> str:
    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        metadata = hit.document.metadata or {}
        snippet = " ".join(hit.document.page_content.split())
        snippet = snippet[:max_document_chars]
        blocks.append(
            f"[{index}]\n"
            f"title: {metadata.get('title') or metadata.get('source_name') or 'untitled'}\n"
            f"source: {metadata.get('source_name') or metadata.get('source_path') or 'unknown'}\n"
            f"author: {metadata.get('author') or 'unknown'}\n"
            f"feature_score: {metadata.get('feature_rerank_score', hit.rerank_score or 0.0):.4f}\n"
            f"retrieval_score: {metadata.get('retrieval_score', hit.fused_score):.4f}\n"
            f"term_overlap: {hit.overlap:.4f}\n"
            f"content: {snippet}\n"
        )

    question_terms = ", ".join(plan.keywords[:8]) or question
    return (
        "You are a retrieval reranker.\n"
        "Rank the candidate passages by how well they support answering the user query.\n"
        "Prefer passages with direct entity matches, exact terminology, and explicit supporting evidence.\n"
        "Penalize broad topical similarity when the subject terms do not line up.\n"
        "Return JSON only in the form {\"ranking\":[{\"candidate\":1,\"score\":0.0,\"reason\":\"...\"}]}\n"
        "Use scores between 0 and 1.\n\n"
        f"Query: {question}\n"
        f"Important query terms: {question_terms}\n\n"
        "Candidates:\n"
        + "\n".join(blocks)
    )


def _parse_llm_rankings(raw_text: str, *, candidate_count: int) -> list[LLMRanking]:
    payload = _extract_json_payload(raw_text)
    if payload is None:
        return []

    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return []

    items = decoded.get("ranking", []) if isinstance(decoded, dict) else decoded
    if not isinstance(items, list):
        return []

    rankings: list[LLMRanking] = []
    seen: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            candidate = int(item.get("candidate"))
            score = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        if candidate < 1 or candidate > candidate_count or candidate in seen:
            continue
        seen.add(candidate)
        reason = " ".join(str(item.get("reason", "")).split())[:240]
        rankings.append(
            LLMRanking(
                candidate=candidate,
                score=min(max(score, 0.0), 1.0),
                reason=reason,
            )
        )
    return rankings


def _extract_json_payload(raw_text: str) -> str | None:
    if not raw_text:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", raw_text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = raw_text.find(start_char)
        end = raw_text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return raw_text[start : end + 1]
    return None


def _copy_hit(hit: RankedDocument, **updates: Any) -> RankedDocument:
    data = {
        "document": hit.document,
        "fused_score": hit.fused_score,
        "overlap": hit.overlap,
        "semantic_rank": hit.semantic_rank,
        "semantic_score": hit.semantic_score,
        "lexical_rank": hit.lexical_rank,
        "lexical_score": hit.lexical_score,
        "rerank_score": hit.rerank_score,
        "matched_terms": hit.matched_terms,
        "matched_term_count": hit.matched_term_count,
        "title_overlap": hit.title_overlap,
        "exact_phrase_hits": hit.exact_phrase_hits,
        "acronym_hits": hit.acronym_hits,
        "exact_title_match": hit.exact_title_match,
        "exact_source_match": hit.exact_source_match,
    }
    data.update(updates)
    return RankedDocument(**data)


def _normalize(text: str) -> str:
    lowered = text.casefold()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()
