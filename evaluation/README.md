# Evaluation

This folder contains the active, corpus-agnostic evaluation toolchain for the RAG app.

## What Stayed

Source files that are part of the current flow:

- [generate_eval_pack.py](C:/Users/mccat/Desktop/Agentic-Track/evaluation/generate_eval_pack.py): builds a corpus-driven evaluation pack
- [run_eval_pack.py](C:/Users/mccat/Desktop/Agentic-Track/evaluation/run_eval_pack.py): runs the app on that pack
- [score_eval_pack.py](C:/Users/mccat/Desktop/Agentic-Track/evaluation/score_eval_pack.py): scores answers
- [visualize_scores.py](C:/Users/mccat/Desktop/Agentic-Track/evaluation/visualize_scores.py): plots results
- [export_to_csv.py](C:/Users/mccat/Desktop/Agentic-Track/evaluation/export_to_csv.py): exports answers to CSV
- [eval_lib.py](C:/Users/mccat/Desktop/Agentic-Track/evaluation/eval_lib.py): shared helpers

## What The Current Evaluation Tests

The pack is generated from the current corpus. It is not tied to one domain.

Positive cases:

- title lookup from indexed sources
- author lookup when metadata exists
- source-grounded excerpt checks

Negative cases:

- fabricated missing title
- fabricated missing author
- missing acronym or short term
- unsupported external fact

This keeps the benchmark general while still checking abstention behavior.

## End-To-End Flow

Run from the repo root.

### 1) Generate a pack

```bat
.\.venv\Scripts\python.exe evaluation\generate_eval_pack.py --corpus-dir corbus --max-sources 4 --out evaluation\corpus_eval_pack.json
```

### 2) Run the app on the pack

```bat
.\.venv\Scripts\python.exe evaluation\run_eval_pack.py --generate-pack --corpus-dir corbus --vector-db-dir data/chroma --out evaluation\eval_answers.jsonl
```

### 3) Score the answers

```bat
.\.venv\Scripts\python.exe evaluation\score_eval_pack.py --pack evaluation\corpus_eval_pack.json --answers evaluation\eval_answers.jsonl --out evaluation\eval_scores.json
```

### 4) Visualize the results

```bat
.\.venv\Scripts\python.exe evaluation\visualize_scores.py --scores evaluation\eval_scores.json --out evaluation\eval_scores.png
```

### 5) Optional CSV export

```bat
.\.venv\Scripts\python.exe evaluation\export_to_csv.py --rubric evaluation\corpus_eval_pack.json --answers evaluation\eval_answers.jsonl --out evaluation\eval_answers.csv
```

## Docker / Open WebUI

The same evaluation run targets the same RAG stack that is used by Open WebUI.

Start the stack:

```bat
openwebui.bat start
```

Verify:

- RAG API: `http://localhost:8001/health`
- Open WebUI: `http://localhost:3000`

Then run the same commands above.

## Output Files

These files are generated when you run evaluation commands:

- `evaluation/corpus_eval_pack.json`
- `evaluation/eval_answers.jsonl`
- `evaluation/eval_answers.csv`
- `evaluation/eval_scores.json`
- `evaluation/eval_scores.png`

They are intentionally not kept in the repo.

## Test Coverage

Evaluation-specific tests live in:

- [test_eval_pack.py](C:/Users/mccat/Desktop/Agentic-Track/tests/test_eval_pack.py)

Run the full suite:

```bat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
