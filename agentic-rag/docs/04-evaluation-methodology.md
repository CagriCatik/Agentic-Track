# Evaluation Methodology

## Metrics

### Retrieval Quality
| Metric | Description | Target |
|--------|-------------|--------|
| Precision@K | % of top-K docs that are relevant | ≥ 0.70 |
| Source Accuracy | Correct PDF appears in retrieved sources? | ≥ 0.90 |

### Generation Quality
| Metric | Description | Target |
|--------|-------------|--------|
| Faithfulness | Answer grounded in docs? (LLM-as-Judge) | ≥ 0.85 |
| Answer Relevance | Answer addresses the question? (LLM-as-Judge) | ≥ 0.80 |
| Citation Accuracy | Correct source cited in answer text? | ≥ 0.75 |

### System Performance
| Metric | Description | Target |
|--------|-------------|--------|
| E2E Latency | Total query-to-answer time | < 30s |
| Retrieval Latency | ChromaDB search time only | < 2s |

## Golden Dataset

`tests/evaluation/eval_dataset.json` — 10 curated Q&A pairs covering all corpus PDFs.

## LLM-as-a-Judge

Uses the same hallucination and answer grading chains (local Ollama) to evaluate outputs automatically.
