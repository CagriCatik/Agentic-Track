import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.rule import Rule

load_dotenv()

console = Console()


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a specific city."""
    weather_database = {
        "london": "rainy and 15C",
        "dubai": "sunny and 42C",
    }
    return weather_database.get(city.lower(), "weather unknown")


def main() -> None:
    console.print(Rule("[bold blue]Tutorial 04 - Manual ReAct Loop"))

    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    console.print(f"[dim]Model:[/dim] {model_name}")
    console.print(f"[dim]Base URL:[/dim] {base_url}\n")

    llm = ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=0,
    )

    tools = [get_weather]
    tools_map = {tool.name: tool for tool in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        HumanMessage(content="What is the weather like in London?")
    ]

    console.print(
        Panel.fit(
            messages[0].content,
            title="User",
            border_style="cyan",
        )
    )

    max_steps = 5

    for step in range(1, max_steps + 1):
        console.print(Rule(f"[yellow]Loop Step {step}"))
        console.print("[bold]Agent is thinking...[/bold]")

        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            console.print(
                Panel(
                    str(response.content),
                    title="Final Answer",
                    border_style="green",
                )
            )
            break

        console.print(
            f"[magenta]Agent decided to make {len(response.tool_calls)} tool call(s).[/magenta]"
        )

        for tool_call in response.tool_calls:
            console.print(
                Panel(
                    Pretty(tool_call),
                    title=f"Tool Call: {tool_call['name']}",
                    border_style="magenta",
                )
            )

            selected_tool = tools_map[tool_call["name"]]
            observation = selected_tool.invoke(tool_call["args"])

            console.print(
                Panel(
                    str(observation),
                    title="Tool Result",
                    border_style="blue",
                )
            )

            messages.append(
                ToolMessage(
                    content=str(observation),
                    tool_call_id=tool_call["id"],
                )
            )
    else:
        console.print(
            Panel(
                "Agent stopped without reaching a final answer.",
                title="Max Steps Reached",
                border_style="red",
            )
        )


if __name__ == "__main__":
    main()