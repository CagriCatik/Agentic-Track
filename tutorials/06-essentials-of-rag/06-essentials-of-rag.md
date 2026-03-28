# Tutorial 06: RAG Essentials (Embeddings & Vector Databases)

Retrieval-Augmented Generation (RAG) is entirely dependent on generating high-quality vector embeddings and storing them in an optimized database format so they can be retrieved via semantic search.

## The Goal
We will embed three sample sentences into mathematical vectors and store them in an ephemeral in-memory Chroma database. Then we will perform a semantic search query against the database to prove it works.

## Dependencies needed:
```bash
uv add langchain-chroma langchain-openai
```

## The Code

Create a file named `rag_essentials.py`:

```python
import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

def main():
    # 1. Initialize the Embedding Model
    # text-embedding-3-small generates 1536-dimensional vectors
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    print("Embedding model loaded.")
    
    # 2. Prepare our raw knowledge base
    documents = [
        "The company revenue in Q3 2023 was incredibly strong, up 24%.",
        "The company office is located in Seattle, Washington.",
        "The CEO's name is John Doe and he loves fishing."
    ]
    
    print(f"Ingesting {len(documents)} documents into Chroma...")
    
    # 3. Create a Local Vector Database (In-Memory)
    # the .from_texts method automatically embeds the strings and inserts them
    vector_store = Chroma.from_texts(
        texts=documents,
        embedding=embeddings,
        collection_name="tutorial_collection"
    )
    
    # 4. Perform a Semantic Search
    query = "Where is the headquarters?"
    print(f"\nUser Query: '{query}'")
    
    # Retrieve the absolute top 1 most mathematically similar document
    results = vector_store.similarity_search(query, k=1)
    
    # 5. Output the result
    print("\n--- Semantic Search Result ---")
    if results:
        print(f"Matched Document: {results[0].page_content}")
    else:
        print("No match found.")

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run rag_essentials.py
```

## What Happens Under the Hood?
Note that the user queried *"Where is the headquarters?"*. None of those exact words exist in the document: *"The company office is located in Seattle, Washington."* 
However, because the embedding model mathematically understands that "headquarters" and "office" share the same semantic conceptual space, the cosine similarity between the two vectors was extremely high, allowing the Vector Database to successfully pull the document!
