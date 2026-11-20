import pytest

import classifier
import evaluate


def test_golden_set_has_4_tickets_per_category():
    examples = evaluate.load_golden()
    assert len(examples) == 12
    for category in classifier.CATEGORIES:
        count = sum(1 for example in examples if example["category"] == category)
        assert count == 4


def test_both_prompts_have_a_place_for_the_ticket():
    assert "{ticket}" in classifier.load_prompt("v1")
    assert "{ticket}" in classifier.load_prompt("v2")


def test_v2_prompt_has_all_six_parts():
    prompt = classifier.load_prompt("v2")
    for part in ["Role", "Context", "Task", "Output format", "Constraints", "Examples"]:
        assert f"## {part}" in prompt


@pytest.mark.parametrize(
    "answer, expected",
    [
        ("Billing", "Billing"),
        (" technical. ", "Technical"),
        ("**Account**", "Account"),
        ("This ticket is about Billing.", None),
        ("Sales", None),
        ("", None),
    ],
)
def test_get_category(answer, expected):
    assert classifier.get_category(answer) == expected


def test_run_eval_counts_the_right_answers(monkeypatch):
    examples = evaluate.load_golden()

    def fake_ask(prompt, temperature):
        assert temperature == 0
        assert "{ticket}" not in prompt
        if examples[0]["ticket"] in prompt:
            return "Technical"
        for example in examples:
            if example["ticket"] in prompt:
                return example["category"]
        return "no ticket found"

    monkeypatch.setattr(classifier, "ask", fake_ask)

    assert evaluate.run_eval("v2") == (11, 12)


def test_accuracy_text():
    assert evaluate.accuracy_text(8, 12) == "8/12 (66%)"
    assert evaluate.accuracy_text(11, 12) == "11/12 (91%)"
