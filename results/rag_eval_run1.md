# RAG evaluation - run 1 (before the fix)

Passed: 9/10

| # | Type | Question | Result | Answer | Sources | Retrieved pages | Failure |
|---|---|---|---|---|---|---|---|
| 1 | answerable | How long is the password reset link valid? | PASS | The password reset link is valid for 1 hour. | 7 | 7, 7, 4 | - |
| 2 | answerable | How much does the Standard plan cost per user per month? | PASS | The Standard plan costs Rs 999 per user per month. | 2 | 2, 2, 4 | - |
| 3 | answerable | How long is the free trial? | PASS | The free trial lasts 14 days. | 2 | 2, 4, 2 | - |
| 4 | answerable | How many API requests per minute can a Premium workspace send? | PASS | A Premium workspace can send 1,000 API requests per minute. | 9 | 9, 9, 2 | - |
| 5 | answerable | How long do deleted tasks stay in the Trash? | PASS | Deleted tasks remain in the Trash for 30 days. | 4 | 4, 4, 4 | - |
| 6 | answerable | When is the support team available? | FAIL | The support team is available Monday through Saturday, from 9 am to 7 pm India time. | 10 | 10, 3, 1 | generation failure: the right page was found but the answer is wrong |
| 7 | unanswerable | Is there a CloudDesk desktop app for Linux? | PASS | I don't know. | - | 1, 1, 9 | - |
| 8 | unanswerable | How much does the Enterprise plan cost? | PASS | I don't know. | - | 2, 2, 9 | - |
| 9 | unanswerable | Who is the CEO of CloudDesk? | PASS | I don't know. | - | 1, 3, 9 | - |
| 10 | unanswerable | Can I export my projects to Microsoft Project? | PASS | I don't know. | - | 4, 4, 3 | - |
