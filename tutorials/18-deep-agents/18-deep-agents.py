from typing import TypedDict, Literal

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama


class MultiAgentState(TypedDict):
    task: str
    delegation: str
    worker_result: str
    final_answer: str


def supervisor_node(state: MultiAgentState) -> dict[str, str]:
    """
    Supervisor agent:
    decides which specialized worker should handle the task.
    """
    print("\n[SUPERVISOR] Analyzing task...")

    llm = ChatOllama(
        model="glm-4.6:cloud",   # replace with a model from `ollama list`
        temperature=0,
    )

    prompt = f"""
You are a supervisor agent in a hierarchical multi-agent system.

Your job is to decide which worker should handle the user's task.

Available workers:
- math_worker: use for arithmetic, calculations, numbers, multiplication, division, subtraction, addition
- research_worker: use for factual questions, biographies, explanations, historical topics, general knowledge

Rules:
- Output exactly one label only.
- Valid outputs are:
  math_worker
  research_worker

User task:
{state["task"]}
""".strip()

    response = llm.invoke(prompt)
    delegation = response.content.strip()

    if delegation not in {"math_worker", "research_worker"}:
        delegation = "research_worker"

    print(f"[SUPERVISOR] Delegating to: {delegation}")
    return {"delegation": delegation}


def math_worker_node(state: MultiAgentState) -> dict[str, str]:
    """
    Specialized worker for math tasks.
    """
    print("[MATH WORKER] Handling math task...")

    llm = ChatOllama(
        model="gpt-oss:120b-cloud",
        temperature=0,
    )

    prompt = f"""
You are a math specialist.
Solve the user's task carefully.

Rules:
- Be concise.
- If there is a calculation, show the result clearly.
- If possible, provide the final answer in one short sentence.

User task:
{state["task"]}
""".strip()

    response = llm.invoke(prompt)
    result = response.content.strip()

    return {
        "worker_result": result,
        "final_answer": f"[Math Worker] {result}",
    }


def research_worker_node(state: MultiAgentState) -> dict[str, str]:
    """
    Specialized worker for explanation / knowledge tasks.
    """
    print("[RESEARCH WORKER] Handling research task...")

    llm = ChatOllama(
        model="glm-4.6:cloud",
        temperature=0,
    )

    prompt = f"""
You are a research specialist.
Answer the user's question clearly and briefly.

Rules:
- Give a direct answer.
- Keep it easy to understand.
- Do not invent tools or sources.

User task:
{state["task"]}
""".strip()

    response = llm.invoke(prompt)
    result = response.content.strip()

    return {
        "worker_result": result,
        "final_answer": f"[Research Worker] {result}",
    }


def route_to_worker(state: MultiAgentState) -> Literal["math_worker", "research_worker"]:
    """
    Reads the supervisor's routing decision.
    """
    return state["delegation"]  # type: ignore[return-value]


def build_app():
    builder = StateGraph(MultiAgentState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("math_worker", math_worker_node)
    builder.add_node("research_worker", research_worker_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route_to_worker)

    builder.add_edge("math_worker", END)
    builder.add_edge("research_worker", END)

    return builder.compile()


def run_demo(app, task: str) -> None:
    print("\n" + "=" * 70)
    print(f"USER TASK: {task}")

    result = app.invoke(
        {
            "task": task,
            "delegation": "",
            "worker_result": "",
            "final_answer": "",
        }
    )

    print("\n[FINAL STATE]")
    print(result)

    print("\n[FINAL ANSWER]")
    print(result["final_answer"])


def main() -> None:
    app = build_app()

    run_demo(app, "Please multiply 50 by 2.")
    run_demo(app, "Who was Abraham Lincoln?")
    run_demo(app, "What is 125 divided by 5?")
    run_demo(app, "Explain what photosynthesis is in simple terms.")


if __name__ == "__main__":
    main()