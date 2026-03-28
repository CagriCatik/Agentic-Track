import ast
import os
import traceback
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama

load_dotenv()


def get_llm() -> ChatOllama:
    return ChatOllama(
        model=os.environ["OLLAMA_MODEL"],
        base_url=os.environ["OLLAMA_BASE_URL"],
        temperature=0,
    )


def strip_code_fences(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    return text


def python_tool(code: str) -> str:
    """
    Execute model-generated Python code and validate it against tests.
    Returns SUCCESS or a detailed ERROR message.
    """
    code = strip_code_fences(code)

    try:
        ast.parse(code)
    except SyntaxError:
        return "ERROR: SyntaxError\n" + traceback.format_exc()

    namespace: dict[str, Any] = {}
    safe_globals = {
        "__builtins__": __builtins__,
    }

    try:
        exec(code, safe_globals, namespace)
    except Exception:
        return "ERROR: Runtime error while executing generated code\n" + traceback.format_exc()

    func = namespace.get("parse_todos") or safe_globals.get("parse_todos")
    if not callable(func):
        return "ERROR: Function parse_todos(markdown: str) -> list[str] was not defined."

    tests = [
        {
            "input": "- [ ] buy milk\n- [x] done\n- [ ] call mom",
            "expected": ["buy milk", "call mom"],
        },
        {
            "input": "* [ ] finish report\n* [x] archived\n* [ ] send email",
            "expected": ["finish report", "send email"],
        },
        {
            "input": "# Notes\n\n- [ ] task one\nSome text\n- [x] task two\n- [ ] task three",
            "expected": ["task one", "task three"],
        },
        {
            "input": "- [ ]   spaced task   \n- [x] done",
            "expected": ["spaced task"],
        },
        {
            "input": "No todos here",
            "expected": [],
        },
    ]

    try:
        for i, test in enumerate(tests, start=1):
            actual = func(test["input"])
            expected = test["expected"]

            if not isinstance(actual, list):
                return (
                    f"ERROR: Test {i} failed\n"
                    f"Expected return type: list\n"
                    f"Actual return type: {type(actual).__name__}\n"
                    f"Actual value: {actual}"
                )

            if actual != expected:
                return (
                    f"ERROR: Test {i} failed\n"
                    f"Input:\n{test['input']}\n\n"
                    f"Expected:\n{expected}\n\n"
                    f"Actual:\n{actual}"
                )
    except Exception:
        return "ERROR: Exception while running tests\n" + traceback.format_exc()

    return "SUCCESS: All tests passed."


def main() -> None:
    try:
        llm = get_llm()
    except KeyError as exc:
        missing_key = str(exc).strip("'")
        print(f"Missing required environment variable: {missing_key}")
        print("Check your .env file.")
        return
    except Exception as exc:
        print(f"Failed to initialize Ollama: {exc}")
        return

    system_task = (
        "Write Python code that defines exactly one function:\n"
        "parse_todos(markdown: str) -> list[str]\n\n"
        "Requirements:\n"
        "- Extract only unchecked markdown todo items.\n"
        "- Support lines starting with '- [ ]' and '* [ ]'.\n"
        "- Ignore completed items like '- [x]' or '* [x]'.\n"
        "- Trim surrounding whitespace from extracted task text.\n"
        "- Return a list[str].\n"
        "- Output only raw Python code.\n"
        "- Do not include explanations.\n"
        "- Do not include markdown fences.\n"
    )

    messages = [HumanMessage(content=system_task)]

    print("--- Starting Reflexion Simulation ---")

    max_attempts = 5
    success = False
    last_code = ""

    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}...")

        response = llm.invoke(messages)
        candidate_code = strip_code_fences(response.content)
        last_code = candidate_code

        print("Generated code:\n")
        print(candidate_code)
        print()

        tool_result = python_tool(candidate_code)
        print(f"Tool result: {tool_result}\n")

        if tool_result.startswith("SUCCESS"):
            success = True
            print("Task completed successfully.")
            break

        messages.append(AIMessage(content=candidate_code))
        messages.append(
            HumanMessage(
                content=(
                    "Your previous solution failed in the tool environment.\n\n"
                    f"{tool_result}\n\n"
                    "Reflect on the failure and write a corrected full solution.\n"
                    "Output only raw Python code."
                )
            )
        )

    print("\n--- FINAL CODE ---\n")
    print(last_code)

    if not success:
        print("\nThe agent did not solve the task within the retry limit.")


if __name__ == "__main__":
    main()