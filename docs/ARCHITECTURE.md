# Architecture Note

## Agent design

One Gemini agent, one tool-calling loop (`backend/app/agent.py`), no multi-agent orchestration. The brief's example flow — look up an order, identify the account, read the agreement, check policy, compute a number, decide whether to escalate — is sequential tool use by a single reasoner, not a task that benefits from splitting across cooperating agents. A system prompt encodes the source-reliability hierarchy explicitly (see below) rather than leaving conflict resolution to implicit model judgment, and the loop runs up to 6 tool rounds per user turn before forcing a text reply.

## Tool design

Three tools, matching the minimum requirement exactly:

| Tool | Purpose | File |
|---|---|---|
| `search_documents` | Retrieval over policies, SOPs, product docs, and the caller's own agreement | `documents.py` |
| `query_account_data` | Structured lookup/calculation over accounts, orders, tickets | `db.py`, `tools.py` |
| `propose_action` | Stages a state-changing action; never executes itself | `actions.py` |

**The load-bearing design decision: `account_id` is not a parameter the model controls.** It's bound server-side from the caller's session (the Streamlit account switcher, standing in for a real login) and injected into every tool call by `tools.dispatch()`. A tool schema that let the model pass `account_id` would make access control a matter of the model choosing not to misuse it — a prompt-injection or a confused model could then read another customer's contract or orders. Instead, `dispatch()` ignores whatever `account_id` shows up in `tool_input` and always uses the trusted value. `tests/test_access_control.py` proves this by explicitly trying to smuggle a different `account_id` through `tool_input` and asserting it's ignored.

## Document and structured-data handling

**Structured data**: the xlsx has 3 real sheets (`accounts`, `orders`, `tickets`), all under 10 rows. They're loaded into pandas DataFrames once at import time; there is no SQLite layer, because a schema-migration-capable database is solving a scale problem 20 total rows doesn't have. Every getter takes `account_id` and filters before returning anything — this is where access control is actually enforced, not a hint in the system prompt.

**Documents**: 5 active single-page PDFs, chunked by paragraph, indexed with TF-IDF + cosine similarity (scikit-learn), built once at import time. No embedding API calls, no vector database — the corpus is small enough that a keyword-weighted lexical index performs entirely adequately and needs no external service or GPU. `02_Support_Policy_v2_DEPRECATED.pdf` is excluded from `ACTIVE_DOCS` in `config.py` and never loaded into the index at all — a hard filter at ingestion, not something the model has to notice from context.

## Source reliability and conflict handling

Encoded in two places, deliberately redundant:

1. **Structurally**, in `documents.py`: agreement chunks (`05_...`, `06_...`) are filtered per-account before the model ever sees them, and the deprecated doc is never indexed. This is enforced code, not instruction.
2. **In the system prompt** (`agent.py`), a plain-language hierarchy: signed agreement > current policy/SOP > product ops guide (context, not policy) > historical ticket resolutions (low-trust, never authoritative). Applying an unambiguous override (agreement beats general policy for that account) is *not* flagged as a conflict — only genuinely ambiguous conflicts between two current, valid sources get surfaced to the user.

This is also the basis for Problem 2 (Trust & Reliability) — see the product note for the adversarial trap-test set that measures whether the hierarchy actually holds under test rather than just asserting it does.

## Major trade-offs

- **Single agent over multi-agent**: faster to build, easier to reason about and test, and the brief's own examples are single-reasoner multi-step tasks, not tasks needing specialized sub-agents.
- **Lightweight TF-IDF retrieval over hybrid BM25+dense+rerank**: the corpus is 5 single-page documents. A heavier retrieval stack adds infrastructure (embedding calls, a vector store) without improving recall at this scale.
- **Pandas over SQLite**: fewer moving parts for a dataset this small; the trade-off is this would need to change before the dataset grows past what comfortably fits in memory.
- **Mocked auth, mocked action execution**: explicitly allowed by the brief. The account switcher stands in for a verified login; `propose_action`/`execute_action` stand in for a real ticketing system. The parts that matter for the assessment — access-control enforcement and the confirmation gate — work identically regardless of what's behind them.
- **What was cut for time**: see the product note for the full list (internal-ops chatbot, Problem 1, multi-agent orchestration, real auth).
