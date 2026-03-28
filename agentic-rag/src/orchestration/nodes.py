"""Graph node functions — 8 pure functions that read/write AgentState."""

from __future__ import annotations

from langchain_core.documents import Document

from src.orchestration.state import AgentState
from src.llm_interface.chains import (
    get_security_chain,
    get_route_chain,
    get_retrieval_grader,
    get_generation_chain,
    get_hallucination_grader,
    get_answer_grader,
)
from src.retrieval.retriever import get_retriever
from src.config import get_settings


# ── Node 1: Security Scan ───────────────────────────────────────
def security_node(state: AgentState) -> dict:
    """Scan user input for prompt injection attempts."""
    print("🛡️  [security_node] Scanning for prompt injection...")
    settings = get_settings()
    if not settings.orchestration.security_scan_enabled:
        print("    → Security scan disabled. Assuming SAFE.")
        return {"is_safe": "SAFE"}
    result = get_security_chain().invoke({"input": state["question"]})
    verdict = result.strip().upper()
    if "DANGER" in verdict:
        verdict = "DANGER"
    else:
        verdict = "SAFE"
    print(f"    → Verdict: {verdict}")
    return {"is_safe": verdict}


# ── Node 2: Route Query ─────────────────────────────────────────
def route_node(state: AgentState) -> dict:
    """Route the question to vectorstore or direct LLM."""
    print("🔀  [route_node] Deciding data source...")
    settings = get_settings()
    if not settings.orchestration.routing_enabled:
        print("    → Routing disabled. Defaulting to vectorstore.")
        return {"datasource": "vectorstore"}
    result = get_route_chain().invoke({"question": state["question"]})
    datasource = result.strip().lower()
    if "vectorstore" in datasource:
        datasource = "vectorstore"
    else:
        datasource = "direct_llm"
    print(f"    → Routing to: {datasource}")
    return {"datasource": datasource}


# ── Node 3: Retrieve Documents ──────────────────────────────────
def retrieve_node(state: AgentState) -> dict:
    """Retrieve relevant documents from ChromaDB."""
    print("📥  [retrieve_node] Querying vector store...")
    retriever = get_retriever()
    documents = retriever.invoke(state["question"])
    print(f"    → Retrieved {len(documents)} documents")
    for i, doc in enumerate(documents):
        src = doc.metadata.get("source_file", "?")
        page = doc.metadata.get("page_start", "?")
        print(f"      [{i+1}] {src}, Seite {page}")
    return {"documents": documents}


# ── Node 4: Grade Documents ─────────────────────────────────────
def grade_documents_node(state: AgentState) -> dict:
    """Grade each retrieved document for relevance, filter irrelevant ones."""
    print("📝  [grade_documents_node] Grading relevance...")
    settings = get_settings()
    
    if not settings.orchestration.document_grading_enabled:
        print(f"    → Grading disabled. Proceeding with {len(state['documents'])} documents.")
        return {"documents": state["documents"], "web_search_needed": "no"}

    grader = get_retrieval_grader()
    question = state["question"]
    documents = state["documents"]

    relevant_docs = []
    web_search_needed = "no"

    for doc in documents:
        result = grader.invoke({
            "question": question,
            "document": doc.page_content,
        })
        grade = result.strip().lower()

        if "yes" in grade:
            relevant_docs.append(doc)
        else:
            web_search_needed = "yes"

    print(f"    → {len(relevant_docs)}/{len(documents)} relevant, web_search={web_search_needed}")
    return {"documents": relevant_docs, "web_search_needed": web_search_needed}


# ── Node 5: Web Search Fallback ─────────────────────────────────
def web_search_node(state: AgentState) -> dict:
    """Fall back to DuckDuckGo when local docs are insufficient."""
    print("🌐  [web_search_node] Searching the web...")
    settings = get_settings()

    try:
        from ddgs import DDGS

        with DDGS() as ddg:
            results = list(
                ddg.text(state["question"], max_results=settings.orchestration.web_search_max_results)
            )

        web_docs = [
            Document(
                page_content=r.get("body", ""),
                metadata={
                    "source_file": r.get("href", "web"),
                    "page_start": 0,
                    "page_end": 0,
                    "section_header": r.get("title", ""),
                },
            )
            for r in results
            if r.get("body")
        ]
        print(f"    → Found {len(web_docs)} web results")
    except Exception as e:
        print(f"    ⚠️  Web search failed: {e}")
        web_docs = []

    # Append web results to existing documents
    existing = state.get("documents", [])
    return {"documents": existing + web_docs, "web_search_needed": "no"}


# ── Node 6: Generate Answer ─────────────────────────────────────
def generate_node(state: AgentState) -> dict:
    """Generate an answer using retrieved context with citations."""
    print("🤖  [generate_node] Generating answer...")

    if state.get("datasource") == "direct_llm":
        from src.llm_interface.chains import get_direct_chat_chain
        result = get_direct_chat_chain().invoke({"question": state["question"]})
        retry = state.get("retry_count", 0) + 1
        print(f"    → Generated directly without context ({len(result)} chars, attempt {retry})")
        return {"generation": result, "retry_count": retry}

    documents = state.get("documents", [])

    # Format context with citation metadata
    context_parts = []
    for i, doc in enumerate(documents):
        src = doc.metadata.get("source_file", "unknown")
        page = doc.metadata.get("page_start", "?")
        section = doc.metadata.get("section_header", "")
        header = f"[Dokument {i+1} | {src}, Seite {page}]"
        if section:
            header += f" ({section})"
        context_parts.append(f"{header}\n{doc.page_content}")

    context = "\n\n---\n\n".join(context_parts)

    result = get_generation_chain().invoke({
        "context": context,
        "question": state["question"],
    })

    retry = state.get("retry_count", 0) + 1
    print(f"    → Generated ({len(result)} chars, attempt {retry})")
    return {"generation": result, "retry_count": retry}


# ── Node 7: Hallucination Check ─────────────────────────────────
def hallucination_check_node(state: AgentState) -> dict:
    """Check if the generated answer is grounded in the documents."""
    print("🔍  [hallucination_check_node] Checking grounding...")
    documents = state["documents"]
    doc_texts = "\n\n".join(d.page_content for d in documents)

    result = get_hallucination_grader().invoke({
        "documents": doc_texts,
        "generation": state["generation"],
    })
    grounded = result.strip().lower()
    print(f"    → Grounded: {grounded}")
    return {}  # routing is handled by conditional edge


# ── Node 8: Answer Relevance Check ──────────────────────────────
def answer_relevance_node(state: AgentState) -> dict:
    """Check if the answer actually addresses the question."""
    print("✅  [answer_relevance_node] Checking relevance...")
    result = get_answer_grader().invoke({
        "question": state["question"],
        "generation": state["generation"],
    })
    relevant = result.strip().lower()
    print(f"    → Relevant: {relevant}")
    return {}  # routing is handled by conditional edge


# ── Routing Functions ────────────────────────────────────────────

def route_after_security(state: AgentState) -> str:
    """Route after security scan."""
    if state.get("is_safe") == "DANGER":
        return "blocked"
    return "route"


def route_after_route(state: AgentState) -> str:
    """Route after query routing."""
    if state.get("datasource") == "vectorstore":
        return "retrieve"
    return "generate"


def route_after_grade(state: AgentState) -> str:
    """Route after document grading."""
    settings = get_settings()
    if state.get("web_search_needed") == "yes" and settings.orchestration.web_search_enabled:
        return "web_search"
    return "generate"


def route_after_hallucination_check(state: AgentState) -> str:
    """Route after hallucination check."""
    settings = get_settings()
    if not settings.orchestration.hallucination_grading_enabled:
        return "answer_relevance"

    documents = state.get("documents", [])
    doc_texts = "\n\n".join(d.page_content for d in documents)

    result = get_hallucination_grader().invoke({
        "documents": doc_texts,
        "generation": state["generation"],
    })
    grounded = result.strip().lower()

    settings = get_settings()
    if "yes" in grounded:
        return "answer_relevance"
    elif state.get("retry_count", 0) >= settings.orchestration.max_hallucination_retries:
        return "answer_relevance"  # Give up retrying, proceed anyway
    return "regenerate"


def route_after_answer_relevance(state: AgentState) -> str:
    """Route after answer relevance check."""
    settings = get_settings()
    if not settings.orchestration.relevance_grading_enabled:
        return "end"

    result = get_answer_grader().invoke({
        "question": state["question"],
        "generation": state["generation"],
    })
    relevant = result.strip().lower()

    if "yes" in relevant:
        return "end"

    settings = get_settings()
    if settings.orchestration.web_search_enabled:
        return "web_search"
    return "end"
