import json
import sys
from pathlib import Path

from extractor import extract_ticket_info
from llm import ask_json

TICKETS_FILE = Path(__file__).parent / "tickets.json"


def ask_with_a_bad_first_answer(messages):
    reply = json.loads(ask_json(messages))
    if len(messages) == 2:
        reply["urgency"] = 10
    return json.dumps(reply)


def main():
    tickets = json.loads(TICKETS_FILE.read_text(encoding="utf-8"))
    demo = "--demo-retry" in sys.argv

    succeeded = 0
    for number, ticket in enumerate(tickets, start=1):
        print(f"\nTicket {number}: {ticket}")
        if demo and number == 1:
            print("(demo: the first answer is changed to urgency 10 to show the retry)")
            result = extract_ticket_info(ticket, ask=ask_with_a_bad_first_answer)
        else:
            result = extract_ticket_info(ticket)

        if result.success:
            succeeded += 1
            print(result.data.model_dump_json(indent=2))
        else:
            print(f"Could not extract this ticket. Errors: {result.errors}")

    print(f"\nExtracted {succeeded} of {len(tickets)} tickets")


if __name__ == "__main__":
    main()
