#!/usr/bin/env python3
import argparse
import json
import csv
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Export QA results to CSV.")
    parser.add_argument("--rubric", required=True, help="Path to evaluation pack/rubric JSON")
    parser.add_argument("--answers", required=True, help="Path to answers JSONL")
    parser.add_argument("--out", required=True, help="Path to output CSV")
    args = parser.parse_args()

    rubric_path = Path(args.rubric)
    answers_path = Path(args.answers)
    out_path = Path(args.out)

    if not rubric_path.exists():
        print(f"Error: Rubric file not found: {rubric_path}", file=sys.stderr)
        return 1
        
    if not answers_path.exists():
        print(f"Error: Answers file not found: {answers_path}", file=sys.stderr)
        return 1

    # Load pack to get prompt text
    with open(rubric_path, "r", encoding="utf-8-sig") as f:
        rubric_data = json.load(f)

    rows = rubric_data.get("cases") or rubric_data.get("questions", [])
    question_map = {
        item["id"]: item.get("prompt") or item.get("question") or ""
        for item in rows
        if isinstance(item, dict) and "id" in item
    }

    # Load answers
    answers = []
    with open(answers_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            answers.append(json.loads(line))

    # Write CSV
    with open(out_path, "w", encoding="utf-8-sig", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow(["Case ID", "Prompt", "Generated Answer"])
        
        for ans in answers:
            qid = ans.get("id", "UNKNOWN")
            answer_text = ans.get("answer", "")
            question_text = question_map.get(qid, "Question text not found in rubric")
            writer.writerow([qid, question_text, answer_text])

    print(f"Successfully exported {len(answers)} answers to {out_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
