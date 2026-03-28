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