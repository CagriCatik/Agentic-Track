"""Generic hybrid retrieval over dense vectors and SQLite FTS."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from .catalog import get_catalog_path, search_catalog

GENERIC_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "author",
    "at",
    "auf",
    "aus",
    "be",
    "bei",
    "block",
    "by",
    "cite",
    "citing",
    "das",
    "dem",
    "den",
    "der",
    "des",
    "die",
    "ein",
    "eine",
    "einem",
    "einer",
    "eines",
    "for",
    "from",
    "fuer",
    "für",
    "give",
    "gib",
    "how",
    "ich",
    "im",
    "in",
    "indexed",
    "into",
    "is",
    "ist",
    "it",
    "list",
    "mit",
    "of",
    "on",
    "or",
    "show",
    "that",
    "the",
    "tell",
    "this",
    "to",
    "und",
    "von",
    "was",
    "we",
    "wer",
    "what",
    "when",
    "where",
    "which",
    "wie",
    "with",
    "wo",
    "who",
    "why",
    "you",
    "your",
    "wrote",
    "written",
    "warum",
    "welche",
    "welcher",
    "welches",
    "welchen",
    "erklaere",
    "erkläre",
    "beschreibe",
    "definiere",
    "define",
    "describe",
    "document",
    "explain",
    "exact",
    "file",
    "source",
    "support",
    "supporting",
    "title",
    "zeige",
    "nenne",
}

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9ÄÖÜäöüß][A-Za-z0-9ÄÖÜäöüß._-]*")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueryPlan:
    raw_query: str
    keywords: list[str]
    quoted_phrases: list[str]
    uppercase_terms: list[str]
    token_count: int
    is_short_query: bool


@dataclass(frozen=True)
class RankedDocument:
    document: Document
    fused_score: float
    overlap: float
    semantic_rank: int | None = None
    semantic_score: float | None = None
    lexical_rank: int | None = None
    lexical_score: float | None = None
    rerank_score: float | None = None
    matched_terms: tuple[str, ...] = ()
    matched_term_count: int = 0
    title_overlap: float = 0.0
    exact_phrase_hits: int = 0
    acronym_hits: int = 0
    exact_title_match: bool = False
    exact_source_match: bool = False


@dataclass(frozen=True)
class RetrievalBundle:
    query: str
    plan: QueryPlan
    hits: list[RankedDocument]

    @property
    def documents(self) -> list[Document]:
        return [hit.document for hit in self.hits]


class HybridRetriever:
    """Combine semantic similarity with lexical FTS retrieval."""

    def __init__(
        self,
        *,
        vector_store: Any,
        vector_db_dir: str | Path,
        top_k: int,
        reranker: Any | None = None,
        semantic_k: int | None = None,
        lexical_k: int | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.catalog_path = get_catalog_path(vector_db_dir)
        self.top_k = top_k
        self.reranker = reranker
        self.semantic_k = semantic_k or max(top_k * 4, 12)
        self.lexical_k = lexical_k or max(top_k * 4, 12)

    def invoke(self, question: str) -> list[Document]:
        return self.search(question).documents

    def search(self, question: str) -> RetrievalBundle:
        plan = plan_query(question)
        logger.info(
            "Planning retrieval: query=%r keywords=%s quoted_phrases=%s uppercase_terms=%s",
            question[:200],
            plan.keywords[:8],
            plan.quoted_phrases[:3],
            plan.uppercase_terms[:4],
        )
        semantic_hits = self._semantic_search(question)
        lexical_hits = self._lexical_search(question, plan)
        logger.info(
            "Retrieved candidates: semantic=%d lexical=%d",
            len(semantic_hits),
            len(lexical_hits),
        )
        ranked = self._fuse_results(plan, semantic_hits, lexical_hits)
        bundle = RetrievalBundle(query=question, plan=plan, hits=ranked)
        if self.reranker is not None:
            bundle = self.reranker.rerank(bundle)
        final_hits = bundle.hits[: self.top_k]
        logger.info(
            "Retrieval ready: top_k=%d top_sources=%s",
            len(final_hits),
            [
                hit.document.metadata.get("source_name", "")
                for hit in final_hits[:5]
                if isinstance(hit.document.metadata, dict)
            ],
        )
        return RetrievalBundle(query=question, plan=plan, hits=final_hits)

    def _semantic_search(self, question: str) -> list[tuple[Document, float]]:
        try:
            results = self.vector_store.similarity_search_with_relevance_scores(
                question,
                k=self.semantic_k,
            )
        except Exception:
            documents = self.vector_store.similarity_search(question, k=self.semantic_k)
            results = [(doc, 0.0) for doc in documents]

        normalized: list[tuple[Document, float]] = []
        for document, score in results:
            metadata = dict(document.metadata or {})
            metadata.setdefault("chunk_id", metadata.get("id", ""))
            normalized.append(
                (
                    Document(page_content=document.page_content, metadata=metadata),
                    float(score),
                )
            )
        return normalized

    def _lexical_search(
        self,
        question: str,
        plan: QueryPlan,
    ) -> list[tuple[Document, float]]:
        expressions = build_match_expressions(question, plan)
        try:
            return search_catalog(
                self.catalog_path,
                expressions=expressions,
                limit=self.lexical_k,
            )
        except Exception:
            return []

    def _fuse_results(
        self,
        plan: QueryPlan,
        semantic_hits: list[tuple[Document, float]],
        lexical_hits: list[tuple[Document, float]],
    ) -> list[RankedDocument]:
        semantic_weight = 1.0 + (0.15 if plan.token_count >= 10 else 0.0)
        lexical_weight = 1.0 + (0.15 if plan.is_short_query else 0.0)
        if plan.uppercase_terms:
            lexical_weight += 0.1
        if plan.quoted_phrases:
            lexical_weight += 0.1

        fused: dict[str, RankedDocument] = {}

        for rank, (document, score) in enumerate(semantic_hits, start=1):
            overlap = compute_overlap(plan, document)
            fused_score = semantic_weight * _rrf(rank)
            if score >= 0.75:
                fused_score += 0.03
            if overlap >= 0.5:
                fused_score += 0.02
            merged = _merge_rank(
                existing=fused.get(_document_key(document)),
                document=document,
                fused_score=fused_score,
                overlap=overlap,
                semantic_rank=rank,
                semantic_score=score,
            )
            fused[_document_key(document)] = merged

        for rank, (document, lexical_score) in enumerate(lexical_hits, start=1):
            overlap = compute_overlap(plan, document)
            fused_score = lexical_weight * _rrf(rank)
            if lexical_score <= -3.0:
                fused_score += 0.02
            if overlap >= 0.5:
                fused_score += 0.03
            merged = _merge_rank(
                existing=fused.get(_document_key(document)),
                document=document,
                fused_score=fused_score,
                overlap=overlap,
                lexical_rank=rank,
                lexical_score=lexical_score,
            )
            fused[_document_key(document)] = merged

        ranked = sorted(
            fused.values(),
            key=lambda item: (item.fused_score, item.overlap),
            reverse=True,
        )
        return [_decorate_ranked_document(hit) for hit in ranked]


def plan_query(question: str) -> QueryPlan:
    keywords = extract_keywords(question)
    quoted_phrases = extract_quoted_phrases(question)
    uppercase_terms = [
        token
        for token in re.findall(r"\b[A-Z0-9]{2,16}\b", question)
        if any(char.isalpha() for char in token)
    ]
    token_count = len(_TOKEN_PATTERN.findall(question))
    return QueryPlan(
        raw_query=question,
        keywords=keywords,
        quoted_phrases=quoted_phrases,
        uppercase_terms=uppercase_terms,
        token_count=token_count,
        is_short_query=len(keywords) <= 5,
    )


def build_match_expressions(question: str, plan: QueryPlan) -> list[str]:
    expressions: list[str] = []

    for phrase in plan.quoted_phrases[:3]:
        cleaned_phrase = phrase.replace('"', "")
        expressions.append(f'"{cleaned_phrase}"')

    expressions.extend(plan.uppercase_terms[:4])

    keywords = plan.keywords[:8]
    expressions.extend(_special_token_expressions(keywords))
    if len(keywords) >= 3:
        expressions.append('"' + " ".join(_quote_term(token) for token in keywords[:5]) + '"')
    if len(keywords) >= 2:
        expressions.append(" AND ".join(_quote_term(token) for token in keywords[:5]))
        expressions.append(" OR ".join(_quote_term(token) for token in keywords[:8]))
    elif keywords:
        expressions.append(_quote_term(keywords[0]))

    if not expressions:
        normalized_question = " ".join(_TOKEN_PATTERN.findall(question)[:8]).strip()
        if normalized_question:
            expressions.append(normalized_question)

    deduped: list[str] = []
    for expression in expressions:
        candidate = expression.strip()
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def extract_keywords(question: str, *, keep_stopwords: bool = False) -> list[str]:
    keywords: list[str] = []
    for token in _TOKEN_PATTERN.findall(question):
        normalized = token.strip("._-").casefold()
        if len(normalized) < 2:
            continue
        if not keep_stopwords and normalized in GENERIC_STOPWORDS:
            continue
        if normalized not in keywords:
            keywords.append(normalized)
    return keywords


def extract_quoted_phrases(question: str) -> list[str]:
    phrases: list[str] = []
    for quote_type in ('"', "'", "`"):
        pattern = rf"{re.escape(quote_type)}([^\n{re.escape(quote_type)}]{{2,120}}){re.escape(quote_type)}"
        for match in re.finditer(pattern, question):
            phrase = " ".join(match.group(1).split()).strip()
            if phrase and phrase not in phrases:
                phrases.append(phrase)
    return phrases


def compute_overlap(plan: QueryPlan, document: Document) -> float:
    query_terms = set(plan.keywords[:8])
    query_terms.update(term.casefold() for term in plan.uppercase_terms[:4])
    if not query_terms:
        query_terms = set(extract_keywords(plan.raw_query, keep_stopwords=True)[:6])
    if not query_terms:
        return 0.0

    metadata = document.metadata or {}
    haystack = " ".join(
        part
        for part in [
            str(metadata.get("title", "")),
            str(metadata.get("author", "")),
            str(metadata.get("source_name", "")),
            document.page_content[:1200],
        ]
        if part
    )
    doc_terms = set(extract_keywords(haystack, keep_stopwords=True))
    if not doc_terms:
        return 0.0
    matched = sum(1 for term in query_terms if term in doc_terms)
    return matched / max(1, len(query_terms))


def bundle_from_documents(question: str, documents: list[Document]) -> RetrievalBundle:
    plan = plan_query(question)
    hits = [
        _decorate_ranked_document(
            RankedDocument(
                document=document,
                fused_score=_rrf(rank),
                overlap=compute_overlap(plan, document),
                semantic_rank=rank,
                semantic_score=None,
            )
        )
        for rank, document in enumerate(documents, start=1)
    ]
    return RetrievalBundle(query=question, plan=plan, hits=hits)


def _merge_rank(
    *,
    existing: RankedDocument | None,
    document: Document,
    fused_score: float,
    overlap: float,
    semantic_rank: int | None = None,
    semantic_score: float | None = None,
    lexical_rank: int | None = None,
    lexical_score: float | None = None,
) -> RankedDocument:
    if existing is None:
        return RankedDocument(
            document=document,
            fused_score=fused_score,
            overlap=overlap,
            semantic_rank=semantic_rank,
            semantic_score=semantic_score,
            lexical_rank=lexical_rank,
            lexical_score=lexical_score,
        )

    return RankedDocument(
        document=existing.document,
        fused_score=existing.fused_score + fused_score,
        overlap=max(existing.overlap, overlap),
        semantic_rank=semantic_rank if semantic_rank is not None else existing.semantic_rank,
        semantic_score=semantic_score if semantic_score is not None else existing.semantic_score,
        lexical_rank=lexical_rank if lexical_rank is not None else existing.lexical_rank,
        lexical_score=lexical_score if lexical_score is not None else existing.lexical_score,
    )


def _decorate_ranked_document(hit: RankedDocument) -> RankedDocument:
    metadata = dict(hit.document.metadata or {})
    metadata["retrieval_score"] = round(hit.fused_score, 6)
    metadata["term_overlap"] = round(hit.overlap, 6)
    if hit.semantic_rank is not None:
        metadata["semantic_rank"] = hit.semantic_rank
    if hit.lexical_rank is not None:
        metadata["lexical_rank"] = hit.lexical_rank

    return RankedDocument(
        document=Document(page_content=hit.document.page_content, metadata=metadata),
        fused_score=hit.fused_score,
        overlap=hit.overlap,
        semantic_rank=hit.semantic_rank,
        semantic_score=hit.semantic_score,
        lexical_rank=hit.lexical_rank,
        lexical_score=hit.lexical_score,
        rerank_score=hit.rerank_score,
        matched_terms=hit.matched_terms,
        matched_term_count=hit.matched_term_count,
        title_overlap=hit.title_overlap,
        exact_phrase_hits=hit.exact_phrase_hits,
        acronym_hits=hit.acronym_hits,
        exact_title_match=hit.exact_title_match,
        exact_source_match=hit.exact_source_match,
    )


def _document_key(document: Document) -> str:
    metadata = document.metadata or {}
    return str(
        metadata.get("chunk_id")
        or metadata.get("id")
        or (
            f"{metadata.get('source_key', metadata.get('source_path', ''))}:"
            f"{metadata.get('page', '?')}:{metadata.get('chunk', '?')}"
        )
    )


def _quote_term(term: str) -> str:
    escaped = term.replace('"', "")
    if "." in escaped:
        return f'"{escaped}"'
    if re.fullmatch(r"[A-Za-z0-9ÄÖÜäöüß._-]+", escaped):
        return escaped
    return f'"{escaped}"'


def _rrf(rank: int, *, k: int = 60) -> float:
    return 1.0 / (k + rank)


def _special_token_expressions(tokens: list[str]) -> list[str]:
    expressions: list[str] = []
    for token in tokens:
        if "." not in token and "_" not in token and "-" not in token:
            continue
        normalized = token
        if "." in normalized:
            normalized = normalized.rsplit(".", 1)[0]
        humanized = normalized.replace("_", " ").replace("-", " ").strip()
        if humanized:
            expressions.append(f'"{humanized}"')
            humanized_terms = [part for part in humanized.split() if part]
            if len(humanized_terms) >= 2:
                expressions.append(" AND ".join(_quote_term(term) for term in humanized_terms[:5]))
            else:
                expressions.append(_quote_term(humanized))
        if normalized:
            expressions.append(_quote_term(normalized))
    return expressions
