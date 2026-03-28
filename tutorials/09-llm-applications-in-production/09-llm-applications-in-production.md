# Tutorial 09: LLM Applications in Production

Once your application exits prototyping, simply logging the output to a Python console is insufficient. You need an observability platform to trace exactly how many tokens were used, how long the API calls took, and exactly what internal logic the LLM reasoned through.

## The Goal
LangSmith is the industry standard for production observability. In this tutorial, we will configure an application to trace all background events automatically, simply by setting environment variables.

## Requirements
Ensure you have created a LangSmith API key at [smith.langchain.com](https://smith.langchain.com) and your `.env` file reflects:
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=production_tutorial_09
```

## The Code
LangSmith requires practically no code changes. LangChain natively parses the environment variables and injects the interceptors on your behalf.

Create a file named `tracing.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

def main():
    # Sanity check that tracing is ON
    if os.environ.get("LANGCHAIN_TRACING_V2") != "true":
        print("WARNING: Tracing is not enabled. Set LANGCHAIN_TRACING_V2=true")
        return
        
    print(f"Tracing enabled logging to project: {os.environ.get('LANGCHAIN_PROJECT')}")
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert financial analyst. Explain the concept of inflation to a 5-year-old in one paragraph."),
        ("user", "Explain: {concept}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    print("\nInvoking chain...")
    result = chain.invoke({"concept": "Inflation"})
    print("\nResult:")
    print(result)
    
    print("\nSuccess. 1. Go to https://smith.langchain.com")
    print("2. Navigate to projects and click on 'production_tutorial_09'")
    print("3. You will see a detailed execution trace of the exact prompt, latency, and token cost.")

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run tracing.py
```

## Exploring LangSmith
When you navigate to the LangSmith UI, you will see exactly what text went in, the LLM generations, and any RAG retrieved chunks attached to that specific Run ID. This gives you the superpower to go back in time and debug why an agent hallucinated in production three days ago!
