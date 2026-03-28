# Tutorial 01: Introduction & Environment Setup

This tutorial covers the absolute baseline setup required before writing any Agentic AI code. We will initialize a Python project, set up virtual environments with `uv`, and verify that our API keys are correctly loaded.

## Prerequisites
- Python 3.10+
- `uv` installed (the blazing fast Python package installer)

## 1. Project Scaffolding
Run the following commands in your terminal to create a clean workspace:

```bash
mkdir my_agent_project
cd my_agent_project

# Initialize a uv project
uv init

# Create and activate a Virtual Environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install core dependencies we will need later
uv add langchain langchain-openai python-dotenv
```

## 2. API Key Configuration
Create a `.env` file at the root of your project:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2-your-langsmith-key
LANGCHAIN_PROJECT=tutorial_01
```

## 3. The Sanity Check Script
Create a file named `main.py`. This script will simply load your environment variables and initialize a connection to the OpenAI API just to ensure no authentication errors occur.

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 1. Load the environment variables from the .env file
load_dotenv()

def main():
    print("Checking environment...")
    
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set!")
        
    # 2. Initialize the LLM
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    # 3. Simple invocation
    response = llm.invoke("Say 'System Online' and nothing else.")
    
    print(f"LLM Response: {response.content}")

if __name__ == "__main__":
    main()
```

## Running the Code
Execute the script using the following command:
```bash
uv run main.py
```
If your console prints `System Online`, your environment is perfectly configured to proceed to the next chapter!
