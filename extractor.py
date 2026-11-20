from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from llm import ask_json

MAX_ATTEMPTS = 3
PROMPT_FILE = Path(__file__).parent / "prompts" / "extractor.txt"


class TicketInfo(BaseModel):
    customer_name: str = Field(min_length=1)
    product: str = Field(min_length=1)
    issue_type: Literal["Billing", "Technical", "Account"]
    urgency: int
    summary: str = Field(min_length=1)

    @field_validator("urgency")
    @classmethod
    def urgency_must_be_1_to_5(cls, value):
        if value < 1 or value > 5:
            raise ValueError("urgency must be 1-5")
        return value


class ExtractionResult(BaseModel):
    success: bool
    attempts: int
    data: TicketInfo | None = None
    errors: list[str] = []


def short_errors(error):
    messages = []
    for item in error.errors():
        message = item["msg"].replace("Value error, ", "")
        field = ".".join(str(part) for part in item["loc"])
        if field and field not in message:
            message = f"{field}: {message}"
        messages.append(message)
    return "; ".join(messages)


def extract_ticket_info(ticket, ask=ask_json):
    messages = [
        {"role": "system", "content": PROMPT_FILE.read_text(encoding="utf-8")},
        {"role": "user", "content": f"Ticket:\n{ticket}"},
    ]
    errors = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            reply = ask(messages)
        except Exception as error:
            errors.append(f"model call failed: {error}")
            print(f"Attempt {attempt}: model call failed ({error})")
            return ExtractionResult(success=False, attempts=attempt, errors=errors)

        try:
            info = TicketInfo.model_validate_json(reply)
        except ValidationError as error:
            problem = short_errors(error)
            errors.append(problem)
            print(f"Attempt {attempt}: validation error ({problem})")

            messages.append({"role": "assistant", "content": reply})
            messages.append({
                "role": "user",
                "content": f"Your JSON is not valid: {problem}. "
                           "Fix it and return the whole JSON object again.",
            })
            continue

        print(f"Attempt {attempt}: success")
        return ExtractionResult(success=True, attempts=attempt, data=info, errors=errors)

    print(f"Failed after {MAX_ATTEMPTS} attempts")
    return ExtractionResult(success=False, attempts=MAX_ATTEMPTS, errors=errors)
