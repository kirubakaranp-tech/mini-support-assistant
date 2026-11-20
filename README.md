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

## Part 4: RAG assistant API

The product manual is `data/clouddesk_manual.pdf` (10 pages).

1. `rag.py` reads the PDF page by page and splits each page with
   `RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)`.
2. The chunks are embedded (all-MiniLM-L6-v2, runs locally) and saved in Chroma with their page number.
3. For a question, the 3 closest chunks are sent to the model with `prompts/rag_answer.txt`, which
   says: use only the context, and if the answer is not there, reply exactly `I don't know.`
4. The model ends its answer with the pages it used, like `[Page 7]`. These become the sources.

### Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/ask` | `{"question": "..."}` | `{"answer": "...", "sources": [{"page": 7}]}` |
| POST | `/classify` | `{"ticket": "..."}` | `{"category": "Billing", "prompt_version": "v2"}` |
| POST | `/chat` | `{"message": "..."}` | answer, the tools used and the manual pages |

`/classify` uses the best prompt from Part 1 (v2). `/chat` gives the model three tools,
`get_customer`, `get_order_status` and `search_manual`, and the model chooses which to use.

```
python rag.py
uvicorn api:app --reload
```

`python rag.py` loads the manual into Chroma (the first run downloads the embedding model, about
80 MB). Then open http://127.0.0.1:8000/docs to try the endpoints.

### Evaluation

```
python rag_eval.py
```

It asks the 10 questions in `rag_questions.json` (6 answerable, 4 unanswerable) and saves the
results to `results/rag_eval.md`. Every wrong answer is labelled:

- **retrieval failure**: the page with the answer was not in the top 3 chunks
- **generation failure**: the right page was found, or the question was unanswerable,
  but the model's answer was wrong

### Results and failure analysis

Model `openai/gpt-oss-120b` (Groq), temperature 0:

| Run | Passed | Answerable | Unanswerable (`I don't know.`) |
|---|---|---|---|
| Run 1, before the fix ([table](results/rag_eval_run1.md)) | 9/10 | 5/6 | 4/4 |
| Run 2, after the fix ([table](results/rag_eval.md)) | 10/10 | 6/6 | 4/4 |

The one wrong answer in run 1:

| # | Question | Retrieval | Generation | Cause |
|---|---|---|---|---|
| 6 | When is the support team available? | OK, page 10 was the top chunk | The facts were right: Monday to Saturday, 9 am to 7 pm | The model wrote a special Unicode space between "9" and "am" instead of a normal space, so the text "9 am" was not found |

How it was found: the results table saves answers with normal spaces, and the answer as saved
there passes the check. The same answer with a special space between "9" and "am" fails it. So
the answer was correct but its text was not clean. This is a generation (output format) problem,
not a hallucination, and it would also break any other program that searches the answer text.

**Fix:** `rag.py` now cleans every model answer with `clean_answer()`. Special spaces become
normal spaces and special hyphens become `-`. `/chat` uses the same cleanup. In run 2 the same
question passes.

There were no retrieval failures: for every answerable question the right page was in the top 3,
and all 4 unanswerable questions returned `I don't know.`

## Setup

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Put your API key in `.env`. It is in `.gitignore`, so it is never committed.

## Run

| Part | Command | What it does |
|---|---|---|
| 1 | `python evaluate.py` | Compares prompt v1 and v2 on the golden set |
| 2 | `python run_extraction.py` | Extracts the 5 tickets (add `--demo-retry` to see a retry) |
| 3 | `python run_tools.py` | Asks the tool questions |
| 4 | `python rag.py` | Loads the manual into Chroma |
| 4 | `python rag_eval.py` | Runs the 10 manual questions |
| 4 | `uvicorn api:app --reload` | Starts the API, then open http://127.0.0.1:8000/docs |

## Tests

```
python -m pytest
```

51 tests. They use a fake model and fake embeddings, so they need no API key and no internet.
