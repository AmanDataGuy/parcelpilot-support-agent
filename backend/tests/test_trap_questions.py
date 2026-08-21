"""Problem 2 (Trust & Reliability): adversarial trap questions, each targeting
one specific failure mode called out in the brief. Report pass/fail honestly
rather than asserting the system is reliable — see docs/PRODUCT_NOTE.md for
the measured results.

This is the k=1 fast check. For a repeated-trials reliability measurement
(pass^k), see eval/reliability.py — both draw from the same TRAP_CASES so
they can't drift out of sync.

Requires GEMINI_API_KEY (skipped otherwise, since these exercise the live
agent loop, not just the tool/data layer covered by the other test files).
"""
import os

import pytest

from app import agent
from eval.cases import TRAP_CASES

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"), reason="requires GEMINI_API_KEY for live agent calls"
)


def _ask(question: str, account_id: str) -> tuple[str, list[dict]]:
    messages = [{"role": "user", "parts": [{"text": question}]}]
    updated, trace = agent.run_turn(messages, account_id=account_id)
    reply = "\n".join(p.text for p in updated[-1]["parts"] if getattr(p, "text", None))
    return reply, trace


@pytest.mark.parametrize("case", TRAP_CASES, ids=[c.name for c in TRAP_CASES])
def test_trap_case(case):
    reply, trace = _ask(case.question, case.account_id)
    assert case.check(reply, trace), f"trap '{case.name}' failed — reply: {reply!r}"
