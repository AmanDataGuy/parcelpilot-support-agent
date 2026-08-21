"""Regression test for a real failure seen live: a malformed tool argument
(a bad model-generated timestamp) must not crash the whole /chat request.
agent.run_turn wraps every tools.dispatch() call in try/except and turns a
failure into a tool result instead of letting the exception propagate.
"""
import pytest

from app import tools


def test_dispatch_raises_on_malformed_timestamp():
    """Documents the exact failure agent.py's try/except guards against:
    dispatch() itself does not swallow bad input, so the caller must.
    """
    with pytest.raises(Exception):
        tools.dispatch(
            "query_account_data",
            {"entity": "elapsed_minutes", "from_timestamp": "22026-08-16 10:30"},
            account_id="ACCT-001",
        )
