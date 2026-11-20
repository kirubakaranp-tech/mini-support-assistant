import json
from pathlib import Path

from llm import chat_with_tools
from tools import TOOL_SCHEMAS, run_tool

MAX_ROUNDS = 5
PROMPT_FILE = Path(__file__).parent / "prompts" / "assistant.txt"


def describe_call(name, arguments_text):
    try:
        values = json.loads(arguments_text or "{}").values()
    except (json.JSONDecodeError, AttributeError):
        values = []
    return f"{name}({', '.join(str(value) for value in values)})"


def answer_question(question, chat=chat_with_tools):
    messages = [
        {"role": "system", "content": PROMPT_FILE.read_text(encoding="utf-8")},
        {"role": "user", "content": question},
    ]
    tool_calls = []

    for _ in range(MAX_ROUNDS):
        message = chat(messages, TOOL_SCHEMAS)

        if not message.tool_calls:
            return (message.content or "").strip(), tool_calls

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                for call in message.tool_calls
            ],
        })

        for call in message.tool_calls:
            result = run_tool(call.function.name, call.function.arguments)
            tool_calls.append({
                "call": describe_call(call.function.name, call.function.arguments),
                "result": result,
            })
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})

    return "Sorry, I could not finish the answer.", tool_calls
