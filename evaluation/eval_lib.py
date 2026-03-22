from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ABSTAIN_MARKERS = [
    "i don't know based on the indexed sources",
    "i do not know based on the indexed sources",
    "ich weiss es nicht auf basis der indexierten quellen",
    "ich weiß es nicht auf basis der indexierten quellen",
    "not supported by the indexed sources",
]


def normalize(text: str) -> str:
    return " ".join(str(text).casefold().split())


def answer_is_abstention(text: str) -> bool:
    normalized = normalize(text)
    return any(marker in normalized for marker in ABSTAIN_MARKERS)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_answers(path: Path) -> dict[str, str]:
    if path.suffix.lower() == ".json":
        data = load_json(path)
        if isinstance(data, dict) and "answers" in data and isinstance(data["answers"], list):
            return {str(item.get("id", "")).strip(): str(item.get("answer", "")).strip() for item in data["answers"]}
        if isinstance(data, list):
            return {str(item.get("id", "")).strip(): str(item.get("answer", "")).strip() for item in data if isinstance(item, dict)}
        if isinstance(data, dict):
            return {str(key).strip(): str(value).strip() for key, value in data.items() if key != "answers"}
        raise ValueError(f"Unsupported JSON answers format: {path}")

    answers: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        raw = line.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        answers[str(obj.get("id", "")).strip()] = str(obj.get("answer", "")).strip()
    return answers


def write_answers_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
