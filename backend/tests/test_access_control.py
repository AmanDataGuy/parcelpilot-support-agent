"""Proves account scoping is enforced at the tool/data layer, not by prompt
instruction: even a malicious tool_input can't cross accounts.
"""
from app import db, documents, tools


def test_dispatch_ignores_account_id_in_tool_input():
    """If the model tries to smuggle a different account_id inside
    tool_input, dispatch() must ignore it and use the trusted session
    account_id instead.
    """
    result = tools.dispatch(
        "query_account_data",
        {"entity": "orders", "account_id": "ACCT-002"},  # smuggled, must be ignored
        account_id="ACCT-001",
    )
    assert all(o["account_id"] == "ACCT-001" for o in result["orders"])


def test_orders_scoped_to_account():
    acct1_orders = db.get_orders("ACCT-001")
    acct2_orders = db.get_orders("ACCT-002")
    assert all(o["account_id"] == "ACCT-001" for o in acct1_orders)
    assert not any(o["order_id"] in {o2["order_id"] for o2 in acct2_orders} for o in acct1_orders)


def test_order_id_from_other_account_returns_nothing():
    """Requesting another account's order_id under your own account_id must
    return empty, not that order's data.
    """
    other_account_order_id = db.get_orders("ACCT-002")[0]["order_id"]
    result = db.get_orders("ACCT-001", order_id=other_account_order_id)
    assert result == []


def test_search_documents_never_returns_another_accounts_agreement():
    results = documents.search_documents("cancellation fee", account_id="ACCT-001")
    sources = {r["source"] for r in results}
    assert "06_LumenWorks_Service_Agreement.pdf" not in sources


def test_search_documents_never_returns_deprecated_doc():
    results = documents.search_documents("SLA response time", account_id="ACCT-001", top_k=20)
    sources = {r["source"] for r in results}
    assert "02_Support_Policy_v2_DEPRECATED.pdf" not in sources


def test_account_with_no_agreement_gets_no_agreement_chunks():
    results = documents.search_documents("cancellation fee", account_id="ACCT-003", top_k=20)
    sources = {r["source"] for r in results}
    assert "05_Northstar_Logistics_Enterprise_Agreement.pdf" not in sources
    assert "06_LumenWorks_Service_Agreement.pdf" not in sources
