"""FastAPI app: chat + confirm endpoints, and the account switcher.

ponytail: no auth framework, no JWT, no cookie session — the assessment
explicitly allows mocked auth. One in-memory message history per account_id
stands in for "logged in as this customer"; a real deployment would replace
just the account_id resolution (from a verified token) and leave everything
downstream of it untouched, since access control is already enforced at the
tool layer (see tools.py), not here.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import actions, agent, db

app = FastAPI(title="ParcelPilot Support Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# account_id -> Anthropic-format message history. Demo-scale only: one
# concurrent conversation per account, no persistence across restarts.
_SESSIONS: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    account_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    trace: list[dict]
    pending_actions: list[dict]


class ConfirmRequest(BaseModel):
    action_id: str


def _known_account_ids() -> set[str]:
    return set(db.ACCOUNTS["account_id"])


def _final_text(parts) -> str:
    return "\n".join(p.text for p in parts if getattr(p, "text", None)).strip()


@app.get("/accounts")
def list_accounts():
    """Powers the UI's account switcher dropdown."""
    return db._rows_to_records(db.ACCOUNTS[["account_id", "account_name", "plan"]])


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if req.account_id not in _known_account_ids():
        raise HTTPException(status_code=404, detail=f"Unknown account_id: {req.account_id}")

    messages = _SESSIONS.setdefault(req.account_id, [])
    messages.append({"role": "user", "parts": [{"text": req.message}]})

    updated_messages, trace = agent.run_turn(messages, account_id=req.account_id)
    _SESSIONS[req.account_id] = updated_messages

    last_response_parts = updated_messages[-1]["parts"]
    pending = [
        step["result"]
        for step in trace
        if step["tool"] == "propose_action" and step["result"].get("status") == "pending_confirmation"
    ]
    return ChatResponse(reply=_final_text(last_response_parts), trace=trace, pending_actions=pending)


@app.post("/confirm")
def confirm(req: ConfirmRequest):
    """The only path that actually executes a proposed action. Never called
    by the agent itself — only by an explicit user click in the UI.
    """
    try:
        return actions.execute_action(req.action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
