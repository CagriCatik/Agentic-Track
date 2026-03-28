# Tutorial 02: The Hello World Chain

In LangChain, the fundamental architectural building block is the **Chain**. A chain links together a Prompt Template, an LLM, and an Output Parser. Since the introduction of LCEL (LangChain Expression Language), writing these chains has become highly declarative using the `|` (pipe) operator.

## The Goal
We will build a simple chain that takes a topic from a user, formats it into a prompt, generates a joke using an LLM, and parses the output as a clean string.

## The Code

Create a file named `02-hello-world-chain.py`:

```python
import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

load_dotenv()

console = Console()


def run_chain():
    console.print(Rule("[bold blue]Hello Chain (Ollama + LangChain)"))

    # 1. Initialize the components
    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    console.print(f"[dim]Model:[/dim] {model_name}")
    console.print(f"[dim]Base URL:[/dim] {base_url}\n")

    llm = ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=0.7,
    )

    output_parser = StrOutputParser()

    # 2. Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a hilarious stand-up comedian. Write a short, single-paragraph joke about the topic provided."),
        ("user", "{topic}")
    ])

    # 3. Chain
    joke_chain = prompt | llm | output_parser

    # 4. Invoke
    topic = "Software engineers debugging in production"

    console.print(Panel.fit(
        f"[bold]Topic:[/bold] {topic}",
        border_style="cyan"
    ))

    console.print("[yellow]Generating joke...[/yellow]\n")

    result = joke_chain.invoke({"topic": topic})

    console.print(Panel(
        Text(result, style="white"),
        title="[bold green]LLM Response[/bold green]",
        border_style="green"
    ))


if __name__ == "__main__":
    run_chain()
```

## How It Works
1. **ChatPromptTemplate:** We define a system instruction safely insulated from user input. The `{topic}` variable is dynamic.
2. **The Pipe Operator (`|`):** This is LCEL. It takes the formatted prompt, pipes it to the LLM, and pipes the raw `AIMessage` returned into the `StrOutputParser` which extracts only the text.
3. **.invoke():** This triggers the synchronous execution of the chain.

## Running the Code
```bash
uv run 02-hello-world-chain.py
```
