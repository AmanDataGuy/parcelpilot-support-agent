"""Central config: paths, model name, and the fixed dataset "now".

ponytail: no settings framework (pydantic-settings, dynaconf) for a handful
of values — plain module-level constants read from env are enough.
"""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR.parent / "data" / "raw"
INDEX_CACHE_DIR = BACKEND_DIR.parent / "data" / "cache"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = os.environ.get("PARCELPILOT_MODEL", "gemini-2.5-flash")

# The workbook's README sheet states the dataset was snapshotted at this
# instant. All SLA/elapsed-time math must be computed against this fixed
# "now", not the real wall clock, or every answer would drift as time passes.
DATASET_TZ = ZoneInfo("Asia/Kolkata")
DATASET_NOW = datetime(2026, 8, 16, 11, 0, tzinfo=DATASET_TZ)

# Deprecated policy doc: excluded from the retrieval index at ingestion time
# (see Section 3 of parcelpilot_spec.md) — never surfaced, not just downweighted.
DEPRECATED_DOC = "02_Support_Policy_v2_DEPRECATED.pdf"

ACTIVE_DOCS = [
    "01_Support_Policy_v3_CURRENT.pdf",
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
    "04_Product_Operations_Guide_and_Known_Issues.pdf",
    "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    "06_LumenWorks_Service_Agreement.pdf",
]

# account_id -> the one agreement PDF that overrides general policy for that
# account. Accounts absent from this map have no override (general policy applies).
ACCOUNT_AGREEMENTS = {
    "ACCT-001": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    "ACCT-002": "06_LumenWorks_Service_Agreement.pdf",
}
