"""Regression test for a real bug found live: two conversations for the same
account must never share server-side history. Before this fix, _SESSIONS was
keyed by account_id alone, so a second person (or the same person testing
twice) asking the same account's questions would silently continue someone
else's conversation — the model would say "I already proposed this" without
actually calling propose_action again, because from its point of view it had.

agent.run_turn is mocked here so this test needs no GEMINI_API_KEY and costs
no API calls — it's testing main.py's session keying, not model behavior.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class _FakePart:
    def __init__(self, text):
        self.text = text
        self.function_call = None


def _fake_run_turn(messages, account_id):
    messages.append({"role": "model", "parts": [_FakePart(f"reply #{len(messages)}")]})
    return messages, []


def test_same_account_different_sessions_do_not_share_history():
    client = TestClient(app)
    with patch("app.main.agent.run_turn", side_effect=_fake_run_turn):
        resp_a = client.post("/chat", json={"account_id": "ACCT-001", "session_id": "session-a", "message": "hi"})
        resp_b = client.post("/chat", json={"account_id": "ACCT-001", "session_id": "session-b", "message": "hi"})

    # Both are the first turn of their own conversation — if history had
    # bled from session-a into session-b, session-b's reply would reflect a
    # longer message list instead of starting fresh.
    assert resp_a.json()["reply"] == "reply #1"
    assert resp_b.json()["reply"] == "reply #1"
