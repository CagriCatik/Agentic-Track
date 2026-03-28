# Tutorial 07: Building a Documentation Assistant

Now that we understand Vector Databases, we must actually hook the database up to a Large Language Model to form a complete RAG pipeline.

## The Goal
Create a production-ready RAG chain. We will build an in-memory database, convert it into a `Retriever` object, and use LCEL to pipe retrieved context directly into a conversational prompt template.

## Dependencies needed:
```bash
uv add langchain langchain-openai langchain-chroma
```

## The Code

Create a file named `doc_assistant.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

def format_docs(docs):
    """Utility function to concatenate document chunks into a single string"""
    return "\n\n".join(doc.page_content for doc in docs)

def main():
    # 1. Initialize core tools
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # 2. Build the Document Store
    docs = [
        "Company Policy Version 2.4: All engineering teams must use Python 3.10+.",
        "Company Policy Version 2.4: Vacation days do not roll over to the next year.",
        "Company Policy Version 2.4: The default database is PostgreSQL 14."
    ]
    vector_store = Chroma.from_texts(docs, embeddings)
    
    # 3. Create a Retriever
    # Turn the database into an interface the chain can use, fetching the top 2 results
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    
    # 4. Create the RAG Prompt Template
    template = """You are an internal documentation assistant. Answer the user's question using ONLY the provided context below.
    If the answer is not contained in the context, say "I don't know based on the documentation."
    
    CONTEXT:
    {context}
    
    QUESTION:
    {question}
    """
    prompt = ChatPromptTemplate.from_template(template)
    
    # 5. Build the RAG Chain using LCEL
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    # 6. Execute!
    user_question = "What version of Python are engineers required to use?"
    print(f"User: {user_question}")
    
    response = rag_chain.invoke(user_question)
    
    print(f"\nAssistant: {response}")

if __name__ == "__main__":
    main()
```

## Explanation
1. `RunnablePassthrough()` acts as a placeholder. Whatever string the user types into `.invoke()` is passed straight into the `{question}` variable of the prompt.
2. The user's input string is *also* passed into the `retriever`.
3. The retriever fetches the `docs`, which hit the `format_docs` function, combining them into one massive string of text.
4. That text is injected into the `{context}` variable of the prompt.
5. The LLM receives the prompt safely and summarizes the answer.

## Running the Code
```bash
uv run doc_assistant.py
```
