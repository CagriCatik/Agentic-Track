"""Configuration loader — single source of truth from config.yaml."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import yaml
from pydantic import BaseModel


# ── Section Models ──────────────────────────────────────────────


class LLMConfig(BaseModel):
    chat_model: str = "gpt-oss:20b-cloud"
    embed_model: str = "nomic-embed-text"
    base_url: str = "http://localhost:11434"
    temperature: float = 0
    max_retries: int = 3


class DataConfig(BaseModel):
    bronze_dir: str = "../corpus"
    silver_dir: str = "./data/silver"
    gold_dir: str = "./data/gold/chroma"
    manifest_dir: str = "./data/manifests"


class IngestionConfig(BaseModel):
    parser: str = "docling"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    markdown_headers_to_split: list[list[str]] = [
        ["#", "Header1"],
        ["##", "Header2"],
        ["###", "Header3"],
    ]


class RetrievalConfig(BaseModel):
    top_k: int = 5
    search_type: str = "mmr"
    mmr_diversity: float = 0.3
    collection_name: str = "automotive_docs"


class OrchestrationConfig(BaseModel):
    security_scan_enabled: bool = True
    routing_enabled: bool = True
    document_grading_enabled: bool = True
    hallucination_grading_enabled: bool = True
    relevance_grading_enabled: bool = True
    web_search_enabled: bool = False
    max_hallucination_retries: int = 3
    web_search_max_results: int = 3


class AppConfig(BaseModel):
    gradio_port: int = 7860
    gradio_share: bool = False


# ── Root Config ─────────────────────────────────────────────────


class Settings(BaseModel):
    llm: LLMConfig = LLMConfig()
    data: DataConfig = DataConfig()
    ingestion: IngestionConfig = IngestionConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    orchestration: OrchestrationConfig = OrchestrationConfig()
    app: AppConfig = AppConfig()


# ── Loader ──────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def get_settings(config_path: Path | None = None) -> Settings:
    """Load and cache the application settings from config.yaml."""
    if config_path is None:
        config_path = _PROJECT_ROOT / "config.yaml"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        settings = Settings(**raw)
    else:
        settings = Settings()

    import os
    if "OLLAMA_BASE_URL" in os.environ:
        settings.llm.base_url = os.environ["OLLAMA_BASE_URL"]

    return settings


def resolve_path(relative: str) -> Path:
    """Resolve a path relative to the project root."""
    return (_PROJECT_ROOT / relative).resolve()
