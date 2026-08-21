"""Proves the confirmation gate: propose_action never executes by itself,
and execute_action only succeeds for a proposal that was actually staged.
"""
import pytest

from app import actions


def test_propose_action_does_not_execute():
    proposal = actions.propose_action(
        "create_escalation", {"ticket_id": "TKT-501", "reason": "P1 SLA breached"}, account_id="ACCT-001"
    )
    assert proposal["status"] == "pending_confirmation"
    assert proposal["action_id"] not in {e["action_id"] for e in actions._EXECUTED}


def test_execute_action_after_confirmation_succeeds():
    proposal = actions.propose_action(
        "update_ticket", {"ticket_id": "TKT-504", "note": "matches KI-211"}, account_id="ACCT-001"
    )
    result = actions.execute_action(proposal["action_id"])
    assert result["status"] == "executed"
    assert result["action_id"] == proposal["action_id"]


def test_execute_action_without_prior_proposal_fails():
    with pytest.raises(KeyError):
        actions.execute_action("never-proposed-id")


def test_execute_action_is_not_repeatable():
    """A confirmed action can't be replayed by calling execute_action twice."""
    proposal = actions.propose_action("create_followup_task", {"note": "check back"}, account_id="ACCT-002")
    actions.execute_action(proposal["action_id"])
    with pytest.raises(KeyError):
        actions.execute_action(proposal["action_id"])


def test_invalid_action_type_rejected():
    with pytest.raises(ValueError):
        actions.propose_action("delete_account", {}, account_id="ACCT-001")
