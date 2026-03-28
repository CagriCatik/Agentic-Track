import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from ollama import chat

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.pretty import Pretty

load_dotenv()
console = Console()


class SoapNote(BaseModel):
    subjective: list[str] = Field(
        description="Patient-reported symptoms, history, and complaints"
    )
    objective: list[str] = Field(
        description="Observed facts, measurements, and clinical findings explicitly present in the notes"
    )
    assessment: list[str] = Field(
        description="Clinical interpretations or likely issues based only on the provided notes"
    )
    plan: list[str] = Field(
        description="Reasonable next steps or follow-up actions based only on the provided notes"
    )


def main() -> None:
    console.print(Rule("[bold blue]Tutorial 05 - SOAP Structured Extraction"))

    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")

    medical_notes = """
    Patient came in today. Mr. Robert Smith is complaining about chronic migraines
    and some slight nausea in the mornings. He mentioned he turned 45 a few weeks
    ago and his blood pressure is slightly elevated. He also has a cough.
    """.strip()

    schema = SoapNote.model_json_schema()

    console.print(f"[dim]Model:[/dim] {model_name}\n")
    console.print(
        Panel(
            medical_notes,
            title="Input Notes",
            border_style="cyan",
        )
    )

    prompt = f"""
Convert the following medical notes into a SOAP note.

Return ONLY a JSON object that matches this JSON schema exactly:
{schema}

Rules:
- Do not output markdown
- Do not output any text before or after the JSON
- Use only information present in the notes
- Keep each list item concise
- If a section has limited information, return a short list with the available facts

Medical notes:
{medical_notes}
""".strip()

    response = chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        format=schema,
    )

    raw_json = response.message.content

    console.print(
        Panel(
            raw_json,
            title="Raw Model Output",
            border_style="magenta",
        )
    )

    try:
        soap_note = SoapNote.model_validate_json(raw_json)
    except ValidationError as exc:
        console.print(
            Panel(
                str(exc),
                title="Validation Error",
                border_style="red",
            )
        )
        return

    console.print(
        Panel(
            "S:\n- " + "\n- ".join(soap_note.subjective)
            + "\n\nO:\n- " + "\n- ".join(soap_note.objective)
            + "\n\nA:\n- " + "\n- ".join(soap_note.assessment)
            + "\n\nP:\n- " + "\n- ".join(soap_note.plan),
            title="Parsed SOAP Note",
            border_style="green",
        )
    )

    console.print(
        Panel(
            Pretty(soap_note.model_dump()),
            title="As Dict",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    main()