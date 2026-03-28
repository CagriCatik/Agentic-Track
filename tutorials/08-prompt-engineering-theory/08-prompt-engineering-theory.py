import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)


def build_chain():
    """Create and return the LangChain pipeline using settings from .env."""
    load_dotenv()

    ollama_base_url = os.environ["OLLAMA_BASE_URL"]
    ollama_model = os.environ["OLLAMA_MODEL"]

    llm = ChatOllama(
        model=ollama_model,
        base_url=ollama_base_url,
        temperature=0.3,
    )

    examples = [
        {
            "input": "Could you please help me fix my code?",
            "output": "Sure. Please share the relevant code and describe the issue you are seeing."
        },
        {
            "input": "I need help understanding this error.",
            "output": "Please paste the full error message and the related code snippet, and I will explain it."
        },
        {
            "input": "Why won't my code compile?",
            "output": "To diagnose that, I need the exact compiler error and the code that is failing to compile."
        },
        {
            "input": "Why won't this C code compile?\n\nint main() {\n    printf(\"Hello\")\n    return 0;\n}",
            "output": "The code is missing a semicolon after printf(\"Hello\");. Add the semicolon and it should compile."
        },
    ]

    example_prompt = ChatPromptTemplate.from_messages([
        ("human", "{input}"),
        ("ai", "{output}"),
    ])

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt,
    )

    final_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a professional AI programming assistant. "
            "Respond clearly, directly, and technically. "
            "If the user does not provide enough debugging information, "
            "ask for the exact error message and the relevant code snippet. "
            "If enough information is provided, diagnose the issue and explain the fix."
        ),
        few_shot_prompt,
        ("human", "{user_input}"),
    ])

    chain = final_prompt | llm
    return chain


def run_single_test(chain):
    """Run one built-in test prompt."""
    test_message = "Why won't my code compile?"
    print(f"User: {test_message}")

    response = chain.invoke({"user_input": test_message})
    print(f"\nAssistant: {response.content}\n")


def run_interactive_chat(chain):
    """Start a simple interactive chat loop."""
    print("Interactive mode started.")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("Session ended.")
            break

        if not user_input:
            continue

        response = chain.invoke({"user_input": user_input})
        print(f"\nAssistant: {response.content}\n")


def main():
    try:
        chain = build_chain()
    except KeyError as exc:
        missing_key = str(exc).strip("'")
        print(f"Missing required environment variable: {missing_key}")
        print("Check your .env file.")
        return
    except Exception as exc:
        print(f"Failed to initialize Ollama/LangChain: {exc}")
        return

    print("=== Few-Shot Prompt Engineering with Local Ollama ===\n")
    run_single_test(chain)
    run_interactive_chat(chain)


if __name__ == "__main__":
    main()