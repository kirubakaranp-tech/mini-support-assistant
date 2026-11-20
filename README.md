# Mini Support Assistant

A support assistant for a software company. It classifies tickets, extracts data into validated
JSON, calls tools for customer and order data, and answers product questions from a PDF manual.

## Part 1: Prompt engineering and golden dataset

The classifier sorts a ticket into **Billing**, **Technical** or **Account**.

| File | What it is |
|---|---|
| `prompts/classifier_v1.txt` | A plain one-line prompt |
| `prompts/classifier_v2.txt` | All six parts: Role, Context, Task, Output format, Constraints, Examples |
| `golden.jsonl` | 12 tickets with the right category, 4 per category, including tricky ones |
| `classifier.py` | Fills the ticket into a prompt and reads the category from the reply |
| `evaluate.py` | `run_eval(version)` runs the golden set at temperature 0 and prints the accuracy |

A reply only counts when it is exactly one of the three categories. A sentence like
"This ticket is about Billing" counts as wrong, because the program could not use it.

### Results

Model `openai/gpt-oss-120b` (Groq), temperature 0:

```
v1: 9/12 (75%) | v2: 12/12 (100%)
```

| # | Ticket | Expected | v1 answer | What fixed it in v2 |
|---|---|---|---|---|
| 2 | Our account was suspended because an invoice was not paid | Billing | `**Category:** Billing` | Output format: one word only |
| 4 | We need 3 more seats for new hires | Billing | Account | Context and constraints: buying seats is Billing |
| 7 | The Stripe integration stopped sending payment receipts | Technical | Billing | Constraints: integrations are Technical |

v2 got all 12 right. The plain v1 prompt guesses on tickets that depend on the company's own
rules, and it does not always answer in a form a program can read.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Put your API key in `.env`. It is in `.gitignore`, so it is never committed.

## Run

```
python evaluate.py v1
python evaluate.py v2
python evaluate.py
```

The last command runs both and ends with a line like `v1: 8/12 (66%) | v2: 11/12 (91%)`.

## Tests

```
python -m pytest
```

The tests use a fake model, so they need no API key.
