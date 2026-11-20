import json

import pytest
from pydantic import ValidationError

from extractor import TicketInfo, extract_ticket_info

GOOD = {
    "customer_name": "Rahul",
    "product": "CloudDesk Web",
    "issue_type": "Account",
    "urgency": 5,
    "summary": "The whole team cannot log in.",
}


def answers(*replies):
    calls = []

    def fake_ask(messages):
        calls.append([dict(message) for message in messages])
        reply = replies[len(calls) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply

    return fake_ask, calls


def test_ticket_info_accepts_good_data():
    info = TicketInfo.model_validate_json(json.dumps(GOOD))
    assert info.urgency == 5


@pytest.mark.parametrize("urgency", [0, 6, 10])
def test_urgency_must_be_1_to_5(urgency):
    with pytest.raises(ValidationError, match="urgency must be 1-5"):
        TicketInfo.model_validate_json(json.dumps({**GOOD, "urgency": urgency}))


def test_success_on_first_attempt(capsys):
    fake_ask, _ = answers(json.dumps(GOOD))

    result = extract_ticket_info("ticket text", ask=fake_ask)

    assert result.success
    assert result.attempts == 1
    assert result.data.customer_name == "Rahul"
    assert "Attempt 1: success" in capsys.readouterr().out


def test_retry_sends_the_error_back(capsys):
    bad = json.dumps({**GOOD, "urgency": 10})
    fake_ask, calls = answers(bad, json.dumps(GOOD))

    result = extract_ticket_info("ticket text", ask=fake_ask)

    assert result.success
    assert result.attempts == 2
    assert result.errors == ["urgency must be 1-5"]

    second_call = calls[1]
    assert second_call[-2] == {"role": "assistant", "content": bad}
    assert "urgency must be 1-5" in second_call[-1]["content"]

    output = capsys.readouterr().out
    assert "Attempt 1: validation error (urgency must be 1-5)" in output
    assert "Attempt 2: success" in output


def test_clear_failure_after_3_attempts():
    fake_ask, calls = answers("not json", json.dumps({**GOOD, "urgency": 9}), json.dumps({"customer_name": "Rahul"}))

    result = extract_ticket_info("ticket text", ask=fake_ask)

    assert not result.success
    assert result.attempts == 3
    assert result.data is None
    assert len(result.errors) == 3
    assert len(calls) == 3


def test_model_call_error_does_not_crash():
    fake_ask, _ = answers(RuntimeError("rate limit"))

    result = extract_ticket_info("ticket text", ask=fake_ask)

    assert not result.success
    assert "rate limit" in result.errors[0]
