"""The state-changing tool: propose_action + the confirmation-gated executor.

ponytail: "execution" is mocked (in-memory dicts), per the spec — there is no
real ticketing system to call. What matters for the assessment is the gate
shape, not the backend it eventually points at.

Nothing executes on the first call. propose_action() only returns a proposal
dict with a fresh action_id. The FastAPI layer shows that proposal to the
user and calls execute_action(action_id) itself, and only after the user
explicitly confirms — the model can never reach execute_action directly, it
isn't in the tool schema handed to the agent.
"""
import uuid

VALID_ACTION_TYPES = {"create_escalation", "update_ticket", "create_followup_task"}

_PENDING: dict[str, dict] = {}
_EXECUTED: list[dict] = []


def propose_action(action_type: str, details: dict, account_id: str) -> dict:
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(f"Unknown action_type: {action_type}. Must be one of {VALID_ACTION_TYPES}")
    action_id = str(uuid.uuid4())[:8]
    proposal = {
        "action_id": action_id,
        "action_type": action_type,
        "details": details,
        "account_id": account_id,
        "status": "pending_confirmation",
    }
    _PENDING[action_id] = proposal
    return proposal


def execute_action(action_id: str) -> dict:
    """Called only by the confirm endpoint, never by the agent's tool loop."""
    proposal = _PENDING.pop(action_id, None)
    if proposal is None:
        raise KeyError(f"No pending action with id {action_id} (already executed, or never proposed)")
    result = {**proposal, "status": "executed"}
    _EXECUTED.append(result)
    return result
