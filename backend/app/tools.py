"""Tool schemas (Anthropic tool-use format) and the dispatcher.

Access control, the important part: account_id is NOT a model-controlled
parameter on any tool schema below. It is bound server-side from the caller's
session (see main.py) and injected here — dispatch() ignores whatever the
model might try to pass for it. This is what makes the access-control
requirement enforceable in the data layer rather than resting on the model
choosing to behave.
"""
from . import actions, db, documents

TOOL_SCHEMAS = [
    {
        "name": "search_documents",
        "description": (
            "Search current policies, SOPs, product documentation, and the "
            "caller's own signed customer agreement (if any) for passages "
            "relevant to a question. Returns passages with their source "
            "document and section so you can cite where a rule came from. "
            "Never returns the deprecated policy doc or another account's agreement."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for, e.g. 'cancellation fee after pickup'."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_account_data",
        "description": (
            "Look up the caller's own account, orders, or tickets, or compute "
            "elapsed minutes between two workbook timestamps (or from a "
            "timestamp to the current dataset snapshot time). Only ever "
            "returns data scoped to the caller's own account."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "enum": ["account", "orders", "tickets", "elapsed_minutes"]},
                "order_id": {"type": "string", "description": "Optional, narrows 'orders' to one order."},
                "ticket_id": {"type": "string", "description": "Optional, narrows 'tickets' to one ticket."},
                "from_timestamp": {"type": "string", "description": "Required for 'elapsed_minutes', e.g. '2026-08-16 09:00'."},
                "to_timestamp": {"type": "string", "description": "Optional for 'elapsed_minutes'; defaults to the dataset snapshot 'now'."},
            },
            "required": ["entity"],
        },
    },
    {
        "name": "propose_action",
        "description": (
            "Propose a state-changing action (create an escalation, update a "
            "ticket, or create a follow-up task). This does NOT execute the "
            "action — it only prepares a proposal that will be shown to the "
            "user for explicit confirmation before anything actually happens. "
            "Call this once you've decided an action is warranted; do not ask "
            "the user to confirm yourself in text, the UI handles that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "enum": sorted(actions.VALID_ACTION_TYPES)},
                "details": {
                    "type": "object",
                    "description": "Free-form details of the action, e.g. {\"ticket_id\": \"TKT-501\", \"reason\": \"P1 SLA breached\"}.",
                },
            },
            "required": ["action_type", "details"],
        },
    },
]


def dispatch(tool_name: str, tool_input: dict, account_id: str) -> dict:
    """Run one tool call, with account_id always taken from the trusted
    session argument rather than from tool_input.
    """
    if tool_name == "search_documents":
        return {"results": documents.search_documents(query=tool_input["query"], account_id=account_id)}

    if tool_name == "query_account_data":
        entity = tool_input["entity"]
        if entity == "account":
            return {"account": db.get_account(account_id)}
        if entity == "orders":
            return {"orders": db.get_orders(account_id, order_id=tool_input.get("order_id"))}
        if entity == "tickets":
            return {"tickets": db.get_tickets(account_id, ticket_id=tool_input.get("ticket_id"))}
        if entity == "elapsed_minutes":
            return {
                "elapsed_minutes": db.elapsed_minutes(
                    tool_input["from_timestamp"], tool_input.get("to_timestamp")
                )
            }
        raise ValueError(f"Unknown entity: {entity}")

    if tool_name == "propose_action":
        return actions.propose_action(
            action_type=tool_input["action_type"],
            details=tool_input["details"],
            account_id=account_id,
        )

    raise ValueError(f"Unknown tool: {tool_name}")
