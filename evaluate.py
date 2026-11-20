import json
import sys
from pathlib import Path

from classifier import classify

GOLDEN_FILE = Path(__file__).parent / "golden.jsonl"


def load_golden():
    examples = []
    with open(GOLDEN_FILE, encoding="utf-8") as file:
        for line in file:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def accuracy_text(correct, total):
    percent = correct * 100 // total
    return f"{correct}/{total} ({percent}%)"


def run_eval(version):
    examples = load_golden()
    correct = 0

    print(f"\nPrompt {version}")
    for number, example in enumerate(examples, start=1):
        category, answer = classify(example["ticket"], version)

        if category == example["category"]:
            correct += 1
            result = "OK"
        else:
            result = "WRONG"

        if category is None:
            one_line = " ".join(answer.split())
            category = f'"{one_line[:40]}"'

        print(f"{number:2}. {result:5} expected {example['category']:9} got {category}")

    print(f"{version}: {accuracy_text(correct, len(examples))}")
    return correct, len(examples)


if __name__ == "__main__":
    versions = sys.argv[1:] or ["v1", "v2"]

    scores = []
    for version in versions:
        correct, total = run_eval(version)
        scores.append(f"{version}: {accuracy_text(correct, total)}")

    if len(scores) > 1:
        print()
        print(" | ".join(scores))
