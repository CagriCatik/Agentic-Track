"""RAG chain construction utilities."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_ollama import ChatOllama


def _join_docs(documents: list[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in documents)


def build_chain(
    *,
    chat_model: str,
    temperature: float,
    system_prompt: str,
    retriever,
    ollama_base_url: str | None = None,
):
    if retriever is None:
        raise ValueError("retriever is required")
    llm = ChatOllama(
        model=chat_model,
        temperature=temperature,
        base_url=ollama_base_url,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Question:\n{question}\n\nContext:\n{context}\n\n"
                "Rules:\n"
                "1. Answer only from the context.\n"
                "2. If the context is incomplete, say what is missing.\n"
                "3. Match the user's language.\n"
                "4. Cite source block numbers when possible.",
            ),
        ]
    )

    return (
        {
            "question": RunnablePassthrough(),
            "context": RunnableLambda(lambda question: retriever.invoke(question))
            | RunnableLambda(_join_docs),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
