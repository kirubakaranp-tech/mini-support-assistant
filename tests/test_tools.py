import json
from types import SimpleNamespace

import pytest

import orders_db
from assistant import answer_question
from tools import get_customer, get_order_status, run_tool


@pytest.fixture(autouse=True)
def temporary_database(tmp_path, monkeypatch):
    monkeypatch.setattr(orders_db, "DB_FILE", tmp_path / "orders.db")
    orders_db.create_database()


def test_get_customer():
    result = get_customer(2)
    assert result["found"] is True
    assert result["customer"]["plan"] == "Premium"


def test_get_customer_unknown_id():
    assert get_customer(99) == {"found": False, "error": "There is no customer with id 99."}


def test_get_order_status():
    result = get_order_status(1042)
    assert result["found"] is True
    assert result["order"]["status"] == "out for delivery"
    assert result["order"]["shipped_date"] == "2026-03-12"


def test_get_order_status_unknown_id():
    assert get_order_status(5555) == {"found": False, "error": "There is no order with id 5555."}


def test_unknown_tool_name_is_safe():
    assert run_tool("delete_order", '{"order_id": 1042}') == {"error": "Unknown tool: delete_order"}


@pytest.mark.parametrize("arguments", ['{"customer_id": "two"}', "{}", "not json", None])
def test_bad_arguments_are_safe(arguments):
    assert run_tool("get_customer", arguments) == {"error": "get_customer needs a whole number customer_id."}


def tool_call(call_id, name, arguments):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def fake_model(*replies):
    seen = []

    def chat(messages, tools):
        seen.append(list(messages))
        return replies[len(seen) - 1]

    return chat, seen


def test_two_tools_in_one_question():
    chat, seen = fake_model(
        SimpleNamespace(content=None, tool_calls=[
            tool_call("c1", "get_customer", {"customer_id": 2}),
            tool_call("c2", "get_order_status", {"order_id": 1042}),
        ]),
        SimpleNamespace(content="Customer 2 is on the Premium plan and order 1042 is out for delivery.", tool_calls=None),
    )

    answer, tool_calls = answer_question("Which plan is customer 2 on and where is order 1042?", chat=chat)

    assert [item["call"] for item in tool_calls] == ["get_customer(2)", "get_order_status(1042)"]
    assert answer == "Customer 2 is on the Premium plan and order 1042 is out for delivery."

    tool_messages = [message for message in seen[1] if message["role"] == "tool"]
    assert [message["tool_call_id"] for message in tool_messages] == ["c1", "c2"]
    assert json.loads(tool_messages[0]["content"])["customer"]["plan"] == "Premium"
    assert json.loads(tool_messages[1]["content"])["order"]["status"] == "out for delivery"


def test_tools_called_one_after_another():
    chat, _ = fake_model(
        SimpleNamespace(content=None, tool_calls=[tool_call("c1", "get_customer", {"customer_id": 2})]),
        SimpleNamespace(content=None, tool_calls=[tool_call("c2", "get_order_status", {"order_id": 1042})]),
        SimpleNamespace(content="Done.", tool_calls=None),
    )

    answer, tool_calls = answer_question("question", chat=chat)

    assert [item["call"] for item in tool_calls] == ["get_customer(2)", "get_order_status(1042)"]
    assert answer == "Done."


def test_model_asks_for_a_tool_that_does_not_exist():
    chat, _ = fake_model(
        SimpleNamespace(content=None, tool_calls=[tool_call("c1", "get_weather", {"city": "Chennai"})]),
        SimpleNamespace(content="I can only look up customers and orders.", tool_calls=None),
    )

    answer, tool_calls = answer_question("What is the weather?", chat=chat)

    assert tool_calls[0]["result"] == {"error": "Unknown tool: get_weather"}
    assert answer == "I can only look up customers and orders."


def test_stops_after_too_many_rounds():
    endless = SimpleNamespace(content=None, tool_calls=[tool_call("c1", "get_customer", {"customer_id": 2})])
    chat, seen = fake_model(*[endless] * 5)

    answer, _ = answer_question("question", chat=chat)

    assert answer == "Sorry, I could not finish the answer."
    assert len(seen) == 5
