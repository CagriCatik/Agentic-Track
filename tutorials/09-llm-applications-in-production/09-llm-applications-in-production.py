import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tracers.langchain import wait_for_all_tracers
from langchain_ollama import ChatOllama

# Load the repository-level .env file:
# tutorials/.env
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)

REQUIRED_ENV_VARS: Final[list[str]] = [
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_API_KEY",
]

OPTIONAL_ENV_VARS: Final[list[str]] = [
    "LANGSMITH_PROJECT",
    "LANGSMITH_WORKSPACE_ID",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TEMPERATURE",
    "OLLAMA_TOP_P",
    "OLLAMA_TOP_K",
    "OLLAMA_REPEAT_PENALTY",
    "OLLAMA_NUM_PREDICT",
    "OLLAMA_SEED",
]


def validate_environment() -> bool:
    missing = [key for key in REQUIRED_ENV_VARS if not os.environ.get(key)]

    if missing:
        print("Missing required environment variables:")
        for key in missing:
            print(f" - {key}")
        return False

    tracing_value = os.environ.get("LANGSMITH_TRACING", "").strip().lower()
    if tracing_value != "true":
        print("WARNING: Tracing is not enabled. Set LANGSMITH_TRACING=true")
        return False

    return True


def get_env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        print(f"WARNING: Invalid float for {name}: {value!r}. Using {default}.")
        return default


def get_env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        print(f"WARNING: Invalid int for {name}: {value!r}. Using {default}.")
        return default


def print_runtime_config() -> None:
    print("Runtime configuration:")
    print(f" - .env path: {ENV_PATH}")
    print(f" - LANGSMITH_TRACING: {os.environ.get('LANGSMITH_TRACING')}")
    print(f" - LANGSMITH_ENDPOINT: {os.environ.get('LANGSMITH_ENDPOINT')}")
    print(f" - LANGSMITH_PROJECT: {os.environ.get('LANGSMITH_PROJECT', 'default')}")
    print(
        f" - LANGSMITH_WORKSPACE_ID: "
        f"{os.environ.get('LANGSMITH_WORKSPACE_ID', '(not set)')}"
    )
    print(f" - OLLAMA_BASE_URL: {os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f" - OLLAMA_MODEL: {os.environ.get('OLLAMA_MODEL', 'gpt-oss:120b-cloud')}")


def build_chain():
    model_name = os.environ.get("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    temperature = get_env_float("OLLAMA_TEMPERATURE", 0.7)
    top_p = get_env_float("OLLAMA_TOP_P", 0.9)
    top_k = get_env_int("OLLAMA_TOP_K", 40)
    repeat_penalty = get_env_float("OLLAMA_REPEAT_PENALTY", 1.1)
    num_predict = get_env_int("OLLAMA_NUM_PREDICT", 256)
    seed = get_env_int("OLLAMA_SEED", 42)

    llm = ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repeat_penalty=repeat_penalty,
        num_predict=num_predict,
        seed=seed,
        metadata={
            "ls_provider": "ollama",
            "ls_model_name": model_name,
        },
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert financial analyst. "
                "Explain the concept of inflation to a 5-year-old in one short paragraph.",
            ),
            ("user", "Explain: {concept}"),
        ]
    )

    return prompt | llm | StrOutputParser()


def main() -> int:
    if not validate_environment():
        return 1

    print_runtime_config()

    project_name = os.environ.get("LANGSMITH_PROJECT", "default")
    print(f"\nTracing enabled. Logging to project: {project_name}")

    chain = build_chain()
    concept = "Inflation"

    try:
        print("\nInvoking chain...")
        result = chain.invoke({"concept": concept})

        print("\nResult:")
        print(result)

        print("\nFinished.")
        print("Check LangSmith:")
        print("1. Open https://smith.langchain.com")
        print(f"2. Look in project: {project_name}")
        print("3. If nothing appears, also check the 'default' project")
        print("4. If you use multiple workspaces, set LANGSMITH_WORKSPACE_ID")
        return 0

    except Exception as exc:
        print(f"\nError while invoking chain: {exc}")
        return 1

    finally:
        wait_for_all_tracers()


if __name__ == "__main__":
    raise SystemExit(main())