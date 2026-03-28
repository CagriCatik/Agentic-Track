# Tutorial 19: LangChain Glossary & Debugging

As you transition to production, things will break. Understanding the exact classes LangChain relies on under the hood and how to debug them is critical.

## Key Terminology
1. **Runnable:** Everything in LCEL is a `Runnable`. Prompt templates, LLMs, and Parsers all inherit from `Runnable`. They all share the exact same methods: `.invoke()`, `.stream()`, and `.batch()`.
2. **Document:** An object containing `page_content` (the raw text) and `metadata` (a dictionary of tags like `{source: "wiki", date: "2024"}`).
3. **AIMessage / HumanMessage:** LangChain standardizes all API inputs globally. Instead of OpenAI's specific JSON array formatting, you use `HumanMessage("text")` and LCEL compiles it into the required vendor format automatically.

## Debugging Tool: set_debug

If an LCEL chain is failing silently and you don't want to boot up the entire LangSmith cloud platform, you can enable verbose local CLI debugging natively.

Create `debugging_demo.py`:

```python
import os
from dotenv import load_dotenv
from langchain.globals import set_debug
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

def main():
    # 1. Flip the global debug switch
    set_debug(True)
    
    print("Verbose HTTP and Chain logging is now ON.\n")
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_template("Translate the word {word} to Spanish.")
    
    chain = prompt | llm | StrOutputParser()
    
    # 2. Invoke the chain
    # Watch your terminal explode with detailed execution steps
    response = chain.invoke({"word": "Apple"})
    
    print(f"\nFinal outcome: {response}")

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run debugging_demo.py
```
Instead of just printing `"Manzana"`, the terminal will print a granular tree view of exactly how the Prompt substituted the variables, exactly what the token array looked like when sent to OpenAI, and exactly how the `StrOutputParser` stripped out the raw headers.
