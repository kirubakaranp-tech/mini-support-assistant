import json

from assistant import answer_question
from orders_db import create_database
from tools import run_tool

QUESTIONS = [
    "Which plan is customer 2 on and where is order 1042?",
    "Which plan is customer 99 on?",
    "Where is order 5555?",
]


def main():
    create_database()

    for question in QUESTIONS:
        print(f"\nQuestion: {question}")
        try:
            answer, tool_calls = answer_question(question)
        except Exception as error:
            print(f"Could not answer: {error}")
            continue

        if tool_calls:
            print(" | ".join(f"Tool: {item['call']}" for item in tool_calls))
            for item in tool_calls:
                print(f"  {item['call']} -> {json.dumps(item['result'])}")
        print(f"Answer: {answer}")

    print("\nSafety check: a tool name that does not exist")
    result = run_tool("delete_order", '{"order_id": 1042}')
    print(f"delete_order(1042) -> {result}")


if __name__ == "__main__":
    main()
