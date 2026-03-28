# Tutorial 17: Useful Tools for LLM Applications

Instead of writing every single prompt and text-parser from scratch, the LangChain ecosystem provides massive libraries of pre-built utilities. 

## The Goal
We will explore two of the most critical daily-use tools: `LangChain Hub` (for pulling pre-written expert prompts from the cloud) and `RecursiveCharacterTextSplitter` (for safely breaking up documents before inserting them into Vector Databases).

## Dependencies needed:
```bash
uv add langchain langchain-openai langchainhub
```

## The Code

Create a file named `useful_tools.py`:

```python
import os
from dotenv import load_dotenv
from langchain import hub
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

def main():
    print("--- 1. LangChain Hub ---")
    # Instead of writing a complex ReAct prompt from scratch, we can simply pull 
    # the industry-standard template directly from the cloud.
    # Check out https://smith.langchain.com/hub
    print("Pulling 'hwchase17/react' prompt from Hub...")
    react_prompt = hub.pull("hwchase17/react")
    
    # Let's see what it looks like
    print("\nTemplate Logic:")
    print(react_prompt.template[:300] + "...\n")
    
    
    print("\n--- 2. RecursiveCharacterTextSplitter ---")
    # If a sentence is 500 characters long, we cannot just split it at character 250, 
    # we would chop a word in half! We want it to split on paragraphs first, then sentences, then spaces.
    
    massive_document = """LangChain is a framework for developing applications powered by language models.
    It enables applications that are:
    - Data-aware: connect a language model to other sources of data.
    - Agentic: allow a language model to interact with its environment.
    
    The main value props of LangChain are:
    1. Components: abstractions for working with language models, along with a collection of implementations for each abstraction.
    2. Off-the-shelf chains: a structured assembly of components for accomplishing specific higher-level tasks.
    """
    
    # Initialize the smarter splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,      # Max characters per chunk
        chunk_overlap=20,    # Number of characters to overlap so context isn't lost between chunks
        length_function=len,
    )
    
    chunks = text_splitter.create_documents([massive_document])
    
    print(f"Split document into {len(chunks)} safe chunks.")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i+1}:\n{chunk.page_content}")

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run useful_tools.py
```
You will see that the TextSplitter successfully respects newlines and list items, rather than slicing indiscriminately!
