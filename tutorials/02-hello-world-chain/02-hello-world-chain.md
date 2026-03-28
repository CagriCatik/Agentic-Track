# Tutorial 02: The Hello World Chain

In LangChain, the fundamental architectural building block is the **Chain**. A chain links together a Prompt Template, an LLM, and an Output Parser. Since the introduction of LCEL (LangChain Expression Language), writing these chains has become highly declarative using the `|` (pipe) operator.

## The Goal
We will build a simple chain that takes a topic from a user, formats it into a prompt, generates a joke using an LLM, and parses the output as a clean string.

## The Code

Create a file named `hello_chain.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

def run_chain():
    # 1. Initialize the components
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    output_parser = StrOutputParser()
    
    # 2. Create the Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a hilarious stand-up comedian. Write a short, single-paragraph joke about the topic provided."),
        ("user", "{topic}")
    ])
    
    # 3. Build the Chain using LCEL (LangChain Expression Language)
    # The | operator passes the output of one component as the input to the next.
    joke_chain = prompt | llm | output_parser
    
    # 4. Invoke the chain
    topic = "Software Engineers debugging in production"
    print(f"Generating joke for topic: '{topic}'...\n")
    
    result = joke_chain.invoke({"topic": topic})
    print(result)

if __name__ == "__main__":
    run_chain()
```

## How It Works
1. **ChatPromptTemplate:** We define a system instruction safely insulated from user input. The `{topic}` variable is dynamic.
2. **The Pipe Operator (`|`):** This is LCEL. It takes the formatted prompt, pipes it to `ChatOpenAI`, and pipes the raw `AIMessage` returned by the LLM into the `StrOutputParser` which strips out markdown and metadata, leaving only text.
3. **.invoke():** This triggers the synchronous execution of the chain.

## Running the Code
```bash
uv run hello_chain.py
```
