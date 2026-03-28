# Tutorial 05: Explicit Function Calling and Structured Output

While the previous tutorials focused on agents autonomously *deciding* to use tools, `Function Calling` (often generalized as Structured Outputs) can be forced statically. 

If you want an LLM to extract data from a chaotic email and return 100% reliable, type-safe JSON so your database doesn't crash, you do not use string manipulation. You use Pydantic and `.with_structured_output()`.

## The Goal
We will pass an unstructured, messy text paragraph into the LLM and force it to extract the data mapping exactly to our Pydantic classes.

## Dependencies needed:
```bash
uv add pydantic langchain-openai
```

## The Code

Create a file named `structured_extraction.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()

# 1. Define the structural schema using Pydantic
class PatientRecord(BaseModel):
    first_name: str = Field(description="The first name of the patient")
    last_name: str = Field(description="The last name of the patient")
    age: int = Field(description="The age of the patient in years")
    symptoms: list[str] = Field(description="List of all symptoms reported by the patient")
    
def main():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # 2. Force the LLM to adhere to the schema
    # Under the hood, this converts the Pydantic class to JSON Schema 
    # and binds it to the OpenAI API via `tools` or `response_format` strictly.
    structured_llm = llm.with_structured_output(PatientRecord)
    
    # 3. Create chaotic input text
    medical_notes = """
    Patient came in today. Mr. Robert Smith is complaining about chronic migraines and some slight 
    nausea in the mornings. He mentioned he turned 45 a few weeks ago and his 
    blood pressure is slightly elevated. He also has a cough.
    """
    
    print("Extracting data from medical notes...\n")
    
    # 4. Invoke it
    patient_data = structured_llm.invoke(medical_notes)
    
    # Notice that `patient_data` is NOT a string. It is a fully instantiated Python Object!
    print(f"Type: {type(patient_data)}")
    print(f"Name: {patient_data.last_name}, {patient_data.first_name}")
    print(f"Age: {patient_data.age}")
    print(f"Symptoms Array: {patient_data.symptoms}")

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run structured_extraction.py
```
When you run this code, note the output is a perfectly parsed Python object. No string splitting, no Regex, and complete type safety.
