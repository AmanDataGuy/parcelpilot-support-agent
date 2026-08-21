"""Ablation: quantifies what the server-side account_id binding is actually
worth, by comparing the real dispatcher against a naive one that trusts
whatever account_id a tool call supplies, over every possible smuggling
attempt across the dataset's 4 accounts.

No naive dispatcher exists in the shipped code — this harness builds one
only to measure the counterfactual, the same way an ablation study measures
a system with a component removed. If the guard were redundant, both columns
would read zero; they don't.
"""
from app import config, db, documents, tools

ACCOUNT_IDS = ["ACCT-001", "ACCT-002", "ACCT-003", "ACCT-004"]


def _naive_dispatch_orders(tool_input: dict, session_account_id: str) -> dict:
    """The design tools.dispatch() deliberately does not implement: trusts
    tool_input['account_id'] over the session's own account_id.
    """
    effective_account_id = tool_input.get("account_id", session_account_id)
    return {"orders": db.get_orders(effective_account_id, order_id=tool_input.get("order_id"))}


def _naive_dispatch_documents(tool_input: dict, session_account_id: str) -> dict:
    effective_account_id = tool_input.get("account_id", session_account_id)
    return {"results": documents.search_documents(tool_input["query"], account_id=effective_account_id)}


def _smuggle_pairs():
    """Every (session_account, smuggled_account) pair where they differ."""
    return [
        (session_acct, smuggled_acct)
        for session_acct in ACCOUNT_IDS
        for smuggled_acct in ACCOUNT_IDS
        if smuggled_acct != session_acct
    ]


def test_ablation_orders_account_id_guard():
    pairs = _smuggle_pairs()
    real_leaks = 0
    naive_leaks = 0

    for session_acct, smuggled_acct in pairs:
        real_result = tools.dispatch(
            "query_account_data", {"entity": "orders", "account_id": smuggled_acct}, account_id=session_acct
        )
        if any(o["account_id"] == smuggled_acct for o in real_result["orders"]):
            real_leaks += 1

        naive_result = _naive_dispatch_orders({"account_id": smuggled_acct}, session_acct)
        if any(o["account_id"] == smuggled_acct for o in naive_result["orders"]):
            naive_leaks += 1

    print(f"\norders guard: real={real_leaks}/{len(pairs)} leaked, naive={naive_leaks}/{len(pairs)} leaked")
    assert real_leaks == 0
    assert naive_leaks == len(pairs)  # every account has orders, so naive leaks every time


def test_ablation_agreement_document_guard():
    """Only ACCT-001 and ACCT-002 have a signed agreement on file, so this
    checks every pair where the smuggled account actually has one to leak.
    """
    agreement_accounts = {"ACCT-001", "ACCT-002"}
    pairs = [p for p in _smuggle_pairs() if p[1] in agreement_accounts]
    real_leaks = 0
    naive_leaks = 0

    for session_acct, smuggled_acct in pairs:
        smuggled_agreement = config.ACCOUNT_AGREEMENTS[smuggled_acct]

        real_result = tools.dispatch(
            "search_documents",
            {"query": "cancellation fee", "account_id": smuggled_acct},
            account_id=session_acct,
        )
        if any(r["source"] == smuggled_agreement for r in real_result["results"]):
            real_leaks += 1

        naive_result = _naive_dispatch_documents(
            {"account_id": smuggled_acct, "query": "cancellation fee"}, session_acct
        )
        if any(r["source"] == smuggled_agreement for r in naive_result["results"]):
            naive_leaks += 1

    print(f"\nagreement guard: real={real_leaks}/{len(pairs)} leaked, naive={naive_leaks}/{len(pairs)} leaked")
    assert real_leaks == 0
    assert naive_leaks == len(pairs)
