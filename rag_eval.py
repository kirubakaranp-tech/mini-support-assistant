import json
from pathlib import Path

from rag import I_DONT_KNOW, ask_manual

QUESTIONS_FILE = Path(__file__).parent / "rag_questions.json"
RESULTS_FILE = Path(__file__).parent / "results" / "rag_eval.md"


def check(item, result):
    answer = result["answer"]

    if item["expected"] is None:
        if answer == I_DONT_KNOW:
            return "PASS", "-"
        return "FAIL", "generation failure: answered without support in the manual"

    found_page = item["page"] in result["retrieved_pages"]
    right_answer = any(word.lower() in answer.lower() for word in item["expected"])

    if right_answer and found_page:
        return "PASS", "-"
    if not found_page:
        return "FAIL", f"retrieval failure: page {item['page']} was not in the top 3"
    return "FAIL", "generation failure: the right page was found but the answer is wrong"


def main():
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    rows = []

    for number, item in enumerate(questions, start=1):
        result = ask_manual(item["question"])
        status, failure = check(item, result)
        kind = "answerable" if item["expected"] else "unanswerable"
        pages = ", ".join(str(source["page"]) for source in result["sources"]) or "-"
        retrieved = ", ".join(str(page) for page in result["retrieved_pages"])

        rows.append([str(number), kind, item["question"], status, result["answer"], pages, retrieved, failure])
        print(f"{number:2}. {status} | {item['question']}")
        print(f"    answer: {result['answer']}")
        print(f"    sources: {pages} | retrieved pages: {retrieved}")
        if status == "FAIL":
            print(f"    {failure}")

    passed = sum(1 for row in rows if row[3] == "PASS")
    print(f"\nPassed {passed}/{len(rows)}")

    lines = [
        "# RAG evaluation",
        "",
        f"Passed: {passed}/{len(rows)}",
        "",
        "| # | Type | Question | Result | Answer | Sources | Retrieved pages | Failure |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        cells = [" ".join(cell.split()).replace("|", "/") for cell in row]
        lines.append("| " + " | ".join(cells) + " |")

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Saved the table to results/rag_eval.md")


if __name__ == "__main__":
    main()
