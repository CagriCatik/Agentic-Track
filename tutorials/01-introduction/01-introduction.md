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
Create a file named `01-introduction.py`. This script will load your environment variables and initialize a connection to your local Ollama server to ensure everything is configured correctly.

```python
import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama


# Load environment variables from .env
load_dotenv()


def main() -> None:
    print("Checking local Ollama environment...")

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")

    # temperature: [0.0 - 2.0]
    # - 0.0 → fully deterministic (same output every time)
    # - ~0.2–0.5 → low randomness (good for factual tasks)
    # - ~0.7–1.0 → balanced creativity
    # - >1.0 → highly random, often unstable
    temperature = float(os.getenv("OLLAMA_TEMPERATURE", 0.0))

    # top_p (nucleus sampling): (0.0 - 1.0]
    # - 1.0 → no filtering
    # - 0.8–0.95 → typical range
    # - lower → more focused, safer outputs
    top_p = float(os.getenv("OLLAMA_TOP_P", 0.9))

    # top_k: [1 - ~100+]
    # - limits candidate tokens to top-k probabilities
    # - 1 → deterministic (greedy)
    # - 20–50 → typical range
    # - higher → more diversity
    top_k = int(os.getenv("OLLAMA_TOP_K", 40))

    # repeat_penalty: [1.0 - 2.0+]
    # - 1.0 → no penalty
    # - 1.05–1.2 → mild repetition control
    # - >1.5 → aggressive, may harm fluency
    repeat_penalty = float(os.getenv("OLLAMA_REPEAT_PENALTY", 1.1))

    # num_predict (max tokens to generate): [1 - context_limit]
    # - e.g., 128–512 for short responses
    # - higher → longer outputs, more latency
    num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", 256))

    # seed: integer or None
    # - fixed value → reproducible outputs
    # - None → random each run
    seed = os.getenv("OLLAMA_SEED")
    seed = int(seed) if seed is not None else None

    print(f"Ollama URL: {base_url}")
    print(f"Model: {model_name}")

    llm = ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repeat_penalty=repeat_penalty,
        num_predict=num_predict,
        seed=seed,
    )

    response = llm.invoke("Say 'Hello World - System Online' and nothing else.")

    print(f"LLM Response: {response.content}")


if __name__ == "__main__":
    main()
```

## Running the Code
Execute the script using the following command:
```bash
uv run 01-introduction.py
```
If your console prints `Hello World - System Online`, your environment is perfectly configured to proceed to the next chapter!
