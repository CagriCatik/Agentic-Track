# debugging_demo_extended.py

from langchain_core.globals import set_debug
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama


def main() -> None:
    set_debug(True)

    print("LangChain debug logging is ON.\n")

    llm = ChatOllama(
        model="glm-4.6:cloud",  # replace with your local Ollama model if needed
        temperature=0,
    )

    # 1) Direct model call using LangChain message objects
    print("=== Direct model call with HumanMessage ===")
    direct_response = llm.invoke(
        [HumanMessage(content="Translate the word 'Apple' to Spanish.")]
    )
    print(direct_response.content)

    # 2) LCEL chain using prompt -> model -> parser
    print("\n=== LCEL chain ===")
    prompt = ChatPromptTemplate.from_template(
        "Translate the word {word} to Spanish."
    )
    chain = prompt | llm | StrOutputParser()

    chain_response = chain.invoke({"word": "Apple"})
    print(chain_response)


from langchain_core.globals import set_debug
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama


def main() -> None:
    set_debug(True)

    llm = ChatOllama(
        model="glm-4.6",
        temperature=0,
    )

    print("=== 1) Direct invoke with HumanMessage ===")
    direct_response = llm.invoke([
        HumanMessage(content="Translate 'Apple' to Spanish. Reply with one word only.")
    ])
    print(direct_response.content)

    prompt = ChatPromptTemplate.from_template(
        "Translate the word {word} to Spanish. Reply with one word only."
    )
    chain = prompt | llm | StrOutputParser()

    print("\n=== 2) Chain invoke ===")
    result = chain.invoke({"word": "Apple"})
    print(result)

    print("\n=== 3) Chain batch ===")
    batch_result = chain.batch([
        {"word": "Apple"},
        {"word": "Orange"},
        {"word": "Grape"},
    ])
    print(batch_result)

    print("\n=== 4) Chain stream ===")
    for chunk in chain.stream({"word": "Banana"}):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()