"""Structured-data access: accounts / orders / tickets from the xlsx.

ponytail: the dataset is 3 sheets, <10 rows each. A SQLite layer would add a
schema-migration surface for no benefit — pandas DataFrames loaded once at
import time and filtered by account_id are the whole "database".

Access control lives here, not in the agent's system prompt: every getter
below takes account_id and filters on it before returning anything, so a
compromised or careless prompt cannot leak another account's rows.
"""
import pandas as pd

from . import config

_SHEETS = pd.read_excel(config.DATA_DIR / "ParcelPilot_Assessment_Data.xlsx", sheet_name=None)
ACCOUNTS = _SHEETS["accounts"]
ORDERS = _SHEETS["orders"]
TICKETS = _SHEETS["tickets"]


def _rows_to_records(df: pd.DataFrame) -> list[dict]:
    return df.where(pd.notnull(df), None).to_dict(orient="records")


def get_account(account_id: str) -> dict | None:
    row = ACCOUNTS[ACCOUNTS["account_id"] == account_id]
    records = _rows_to_records(row)
    return records[0] if records else None


def get_orders(account_id: str, order_id: str | None = None) -> list[dict]:
    """Orders for one account, optionally narrowed to one order_id.

    The account_id filter is applied unconditionally: even if order_id
    belongs to a different account, this returns nothing rather than
    silently ignoring the scope.
    """
    df = ORDERS[ORDERS["account_id"] == account_id]
    if order_id is not None:
        df = df[df["order_id"] == order_id]
    return _rows_to_records(df)


def get_tickets(account_id: str, ticket_id: str | None = None) -> list[dict]:
    df = TICKETS[TICKETS["account_id"] == account_id]
    if ticket_id is not None:
        df = df[df["ticket_id"] == ticket_id]
    return _rows_to_records(df)


def elapsed_minutes(from_timestamp: str, to_timestamp: str | None = None) -> float:
    """Minutes between two workbook timestamps, or from a timestamp to the
    fixed dataset snapshot "now" if to_timestamp is omitted.

    Pure arithmetic — not a policy rule. Thresholds (e.g. "30 minutes",
    "2 hours") come from the policy documents via search_documents, and the
    agent combines that text with this number itself.
    """
    start = pd.to_datetime(from_timestamp)
    end = pd.to_datetime(to_timestamp) if to_timestamp else config.DATASET_NOW.replace(tzinfo=None)
    return round((end - start).total_seconds() / 60, 1)
