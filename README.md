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

## Part 2: Structured output with validation

`extractor.py` turns a free-text ticket into a `TicketInfo` object:

| Field | Rule |
|---|---|
| `customer_name` | text, not empty |
| `product` | text, not empty |
| `issue_type` | `Billing`, `Technical` or `Account` |
| `urgency` | whole number from 1 to 5 |
| `summary` | text, not empty |

How it works:

1. The ticket is sent with `prompts/extractor.txt` in JSON mode at temperature 0.
2. The reply is checked with `TicketInfo.model_validate_json`.
3. If the check fails, the error is sent back to the model with the request to fix it.
   This is tried up to 3 times.
4. After 3 failed attempts it returns a failure result with the errors. It never crashes,
   even if the model call itself fails.

```
python run_extraction.py
```

It extracts the 5 tickets in `tickets.json` and prints every attempt, for example:

```
Attempt 1: validation error (urgency must be 1-5)
Attempt 2: success
```

The model often gets it right the first time. To always see a retry, run
`python run_extraction.py --demo-retry`. It changes the model's first answer for ticket 1
to urgency 10, so you can watch the error being sent back and fixed.

## Part 3: Tool calling

The model decides by itself when to use two tools:

| Tool | Data from | Result |
|---|---|---|
| `get_customer(customer_id)` | the `CUSTOMERS` dictionary in `tools.py` | name, plan and email |
| `get_order_status(order_id)` | the `orders` table in a SQLite file, `orders.db` | status and dates |

Every tool returns clean JSON: `{"found": true, ...}` with the data, or `{"found": false, "error": "..."}`.

`assistant.py` runs the tool loop. It sends the question with the tool schemas, runs every tool
the model asks for, sends back the results and repeats until the model answers (at most 5 rounds).

Safety:

- An unknown id returns `There is no customer with id 99.` instead of an error.
- A tool name that does not exist returns `Unknown tool: ...` instead of crashing.
- Ids must be whole numbers, and the SQL uses a `?` parameter, so the model never writes SQL.

```
python run_tools.py
```

It creates `orders.db` and asks the test question, an unknown customer and an unknown order:

```
Question: Which plan is customer 2 on and where is order 1042?
Tool: get_customer(2) | Tool: get_order_status(1042)
Answer: Customer 2 is on the Premium plan and order 1042 is out for delivery.
```

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
