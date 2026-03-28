# Agentic RAG Evaluation Suite

This folder contains the complete evaluation toolchain for the Agentic RAG application. It includes both the native Medallion-architecture LLM Judge pipeline and an adapted corpus-agnostic evaluation pack system.

## 1. Native Agentic RAG Evaluation (Recommended)

The native evaluation suite (`runner.py`) leverages the powerful "LLM-as-a-Judge" technique. It evaluates the current LangGraph application against a predefined dataset without relying on brittle keyword matching. It grades both **Faithfulness** (is the answer grounded in the retrieved context?) and **Answer Relevance** (does the answer address the question?).

### Running the Native Evaluator

```powershell
# Run the pipeline against the default dataset
uv run python evaluation/runner.py --dataset tests/evaluation/eval_dataset.json
```

Reports are automatically saved to the `evaluation/reports/` directory in Markdown format, detailing precision, latency, and LLM Judge verdicts.


### End-To-End Flow

Run these commands from the repository root:

#### 1) Generate an Evaluation Pack
Scans your `data/silver` layer and generates synthetic test cases.
```powershell
uv run python evaluation/generate_eval_pack.py --max-sources 4 --out evaluation/corpus_eval_pack.json
```

#### 2) Run the Evaluation Cases
Feeds the generated questions into the Agentic RAG pipeline and captures the LLM responses.
```powershell
uv run python evaluation/run_eval_pack.py --pack evaluation/corpus_eval_pack.json --out evaluation/eval_answers.jsonl
```

#### 3) Score the Answers
Scores the generated answers against the pack's expectations and validation rules.
```powershell
uv run python evaluation/score_eval_pack.py --pack evaluation/corpus_eval_pack.json --answers evaluation/eval_answers.jsonl --out evaluation/eval_scores.json
```

#### 4) Visualize the Results (Optional)
Generates a PNG bar chart of the scoring matrix.
```powershell
uv run python evaluation/visualize_scores.py --scores evaluation/eval_scores.json --out evaluation/eval_scores.png
```

## Docker & Open WebUI Note

Because the evaluation scripts directly invoke the `src.orchestration.graph` pipeline on your host machine, they bypass the Fast API Docker container. This means you can run the evaluation tests concurrently while the `agentic-rag-backend` and Open WebUI containers are actively running in Docker.
