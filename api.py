from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from assistant import answer_question
from classifier import classify
from rag import I_DONT_KNOW, ask_manual, clean_answer, is_i_dont_know

BEST_PROMPT = "v2"

app = FastAPI(title="Mini Support Assistant")


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class Source(BaseModel):
    page: int


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


class ClassifyRequest(BaseModel):
    ticket: str = Field(min_length=1)


class ClassifyResponse(BaseModel):
    category: str
    prompt_version: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str]
    sources: list[Source]


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    try:
        return ask_manual(request.question)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Could not answer right now: {error}")


@app.post("/classify", response_model=ClassifyResponse)
def classify_ticket(request: ClassifyRequest):
    try:
        category, reply = classify(request.ticket, BEST_PROMPT)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Could not classify right now: {error}")

    if category is None:
        raise HTTPException(status_code=502, detail=f"The model gave an answer that is not a category: {reply}")
    return {"category": category, "prompt_version": BEST_PROMPT}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        answer, tool_calls = answer_question(request.message)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Could not answer right now: {error}")

    sources = []
    for item in tool_calls:
        for chunk in item["result"].get("chunks", []):
            if {"page": chunk["page"]} not in sources:
                sources.append({"page": chunk["page"]})

    answer = clean_answer(answer)
    if is_i_dont_know(answer):
        answer = I_DONT_KNOW
        sources = []

    return {"answer": answer, "tools_used": [item["call"] for item in tool_calls], "sources": sources}
