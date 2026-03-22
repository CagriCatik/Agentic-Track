"""Ollama model discovery and selection heuristics."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

CHAT_PRIORITY = [
    "gpt-oss",
    "qwen2.5-coder",
    "qwen2.5",
    "olmo-3",
    "llama3.3",
    "llama3.1",
    "llama3",
    "qwen3",
    "mistral",
    "gemma",
    "phi4",
    "phi3",
]

EMBEDDING_PRIORITY = [
    "nomic-embed-text",
    "mxbai-embed-large",
    "bge",
    "all-minilm",
    "embed",
]


def _discover_via_cli() -> list[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    models: list[str] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("name "):
            continue
        name = line.split()[0]
        if name and name not in models:
            models.append(name)
    return models


def _discover_via_http(base_url: str | None = None) -> list[str]:
    raw_base = base_url or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434"
    url = f"{raw_base.rstrip('/')}/api/tags"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []

    models: list[str] = []
    for item in payload.get("models", []):
        name = item.get("name")
        if isinstance(name, str) and name and name not in models:
            models.append(name)
    return models


def discover_ollama_models(base_url: str | None = None) -> list[str]:
    """Discover installed model names via CLI, then HTTP fallback."""
    models = _discover_via_cli()
    if models:
        return models
    return _discover_via_http(base_url=base_url)


def _pick_with_priority(models: list[str], ordered_keywords: list[str]) -> str | None:
    lowered = [(model, model.lower()) for model in models]
    candidates: list[tuple[int, float, str]] = []
    for model, lower_name in lowered:
        priority_rank = None
        for index, keyword in enumerate(ordered_keywords):
            if keyword in lower_name:
                priority_rank = index
                break
        if priority_rank is None:
            continue
        size_hint = _extract_size_hint(lower_name)
        candidates.append((priority_rank, -size_hint, model))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1], item[2].lower()))
    return candidates[0][2]


def _extract_size_hint(model_name: str) -> float:
    import re

    match = re.search(r":([0-9]+(?:\.[0-9]+)?)b", model_name)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    if "cloud" in model_name:
        return 999.0
    return 0.0


def infer_chat_model(models: list[str]) -> str | None:
    model = _pick_with_priority(models, CHAT_PRIORITY)
    if model:
        return model
    for model_name in models:
        if "embed" not in model_name.lower():
            return model_name
    return None


def infer_embedding_model(models: list[str]) -> str | None:
    model = _pick_with_priority(models, EMBEDDING_PRIORITY)
    if model:
        return model
    for model_name in models:
        if "embed" in model_name.lower():
            return model_name
    return None


def select_models(
    available_models: list[str],
    forced_chat: str | None = None,
    forced_embedding: str | None = None,
) -> tuple[str | None, str | None]:
    chat_model = forced_chat or infer_chat_model(available_models)
    embedding_model = forced_embedding or infer_embedding_model(available_models)
    return chat_model, embedding_model


def model_exists(name: str, available_models: list[str]) -> bool:
    wanted = name.lower()
    return any(model.lower() == wanted for model in available_models)
