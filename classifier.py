from pathlib import Path

from llm import ask

CATEGORIES = ["Billing", "Technical", "Account"]
PROMPTS_FOLDER = Path(__file__).parent / "prompts"


def load_prompt(version):
    path = PROMPTS_FOLDER / f"classifier_{version}.txt"
    return path.read_text(encoding="utf-8")


def get_category(answer):
    word = answer.strip().strip("*.").strip()
    for category in CATEGORIES:
        if word.lower() == category.lower():
            return category
    return None


def classify(ticket, version):
    prompt = load_prompt(version).replace("{ticket}", ticket)
    answer = ask(prompt, temperature=0)
    return get_category(answer), answer
