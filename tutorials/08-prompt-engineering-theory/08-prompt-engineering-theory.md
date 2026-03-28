# Tutorial 08: Prompt Engineering Theory

Prompting an LLM professionally involves much more than asking it nicely. Constructing dynamic templates that inject few-shot examples or system contexts is the foundation of orchestration.

## The Goal
We will use LangChain's built-in `FewShotChatMessagePromptTemplate` to pass dynamically formatted conversation examples into a model, forcing it to mimic a specific behavioral pattern (a snarky translator).

## Dependencies needed:
```bash
uv add langchain-openai langchain-core
```

## The Code

Create a file named `few_shot_prompting.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)

load_dotenv()

def main():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    # 1. Define hardcoded examples of the behavior we want the model to learn
    examples = [
        {"input": "Could you please help me fix my code?", "output": "Ugh, fine. Show me the mess you've made."},
        {"input": "I need help understanding this error.", "output": "Did you try reading it? No? Okay, let me explain it like you're five."}
    ]
    
    # 2. Create an exact formatting template for *how* these examples should map to Human/AI messages
    example_prompt = ChatPromptTemplate.from_messages([
        ("human", "{input}"),
        ("ai", "{output}")
    ])
    
    # 3. Compile the actual Few-Shot Template
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt
    )
    
    # 4. Combine into final System Prompt
    final_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a highly capable AI, but your persona is incredibly tired and mildly insulting to software engineers."),
        few_shot_prompt,
        ("human", "{user_input}")
    ])
    
    # 5. Build the simple chain
    chain = final_prompt | llm
    
    # 6. Test it with a new input that the model hasn't seen
    test_message = "Why won't my code compile?"
    print(f"User: {test_message}")
    
    response = chain.invoke({"user_input": test_message})
    print(f"\nAssistant: {response.content}")

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run few_shot_prompting.py
```

## Why Few-Shot?
We could have simply told the model in the system prompt: *"Be insulting."* But "insulting" is subjective, and the model might become wildly inappropriate or offensive. By using a Few-Shot wrapper, we lock the style, tone, and formatting to the exact standard defined in our static dataset.
