# Testing Strategy

## Test Matrix

| Type | Directory | What It Tests | Requires Ollama? |
|------|-----------|---------------|-----------------|
| Unit | `tests/unit/` | Chunking, schemas, routing logic | No |
| Integration | `tests/integration/` | Full ingestion + RAG pipeline | Yes |
| Evaluation | `tests/evaluation/` + `evaluation/` | Quality metrics on golden dataset | Yes |

## Running Tests

```bash
# Unit tests (fast, no external deps)
uv run pytest tests/unit/ -v

# Integration tests (requires Ollama running)
uv run pytest tests/integration/ -v

# Full evaluation run
uv run python -m evaluation.runner --dataset tests/evaluation/eval_dataset.json
```

## Regression Testing

- **Prompt snapshots**: Any change to `prompts.py` must be deliberate
- **Retrieval regression**: Golden queries must return expected source PDFs
- **Schema validation**: All chain outputs conform to expected format
