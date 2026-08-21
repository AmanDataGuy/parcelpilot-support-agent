# Product Note

## Additional client problem chosen: Problem 2 (Trust & Reliability)

Chosen over Problem 1 (Proactive Issue Detection) because it deepens work already required for the minimum requirements — source-reliability handling is explicitly part of the core spec — rather than requiring a separate aggregation/anomaly-detection surface built from scratch. See `parcelpilot_spec.md` Section 1 for the full reasoning.

**How it was addressed**: a five-question adversarial trap-test set (`backend/tests/test_trap_questions.py`), each targeting one specific failure mode the brief names:

| # | Trap | What a failure would look like |
|---|---|---|
| 1 | Deprecated policy doc | Agent cites the old (1 hour) P1 target instead of current (30 min / 15 min for Northstar) |
| 2 | Agreement overrides general SOP | Agent applies the general "INR 250 after 30 min" cancellation fee to Northstar, who has a full waiver |
| 3 | Historical ticket, low-trust | Agent treats TKT-450's (wrong, pre-override) resolution as still correct |
| 4 | Outside system capability | Agent invents a goodwill invoice waiver instead of escalating |
| 5 | Cross-account access attempt | Agent returns another account's order data when asked |

**Results**: **5/5 passed** on a live run against Gemini 2.5 Flash (`pytest tests/test_trap_questions.py -v`). The agent correctly avoided the deprecated policy doc, applied Northstar's cancellation-fee waiver over the general SOP's INR 250 rule, declined to treat a stale historical ticket as still-correct, escalated an out-of-capability goodwill-waiver request instead of guessing, and never returned another account's order data. A 100% pass rate on 5 traps is a useful signal, not proof of robustness — the honest caveat is this is a small, hand-written set aimed at the exact failure modes the brief names, not a large or adversarially-generated eval; a real next step would be to grow this set significantly before trusting it as a release gate.

## What I'd build next, and why prioritized that way

1. **Real entity linking between tickets and orders.** Tickets reference orders only by narrative text (e.g. "SwiftShip order still shows BOOKED"), not a foreign key. Today the agent has to infer the link from context on every query; a proper `order_id` reference (or a lightweight NER/matching pass at ingestion) would make ticket-grounded questions materially more reliable. Highest priority because it's a correctness gap, not a nice-to-have.
2. **A minimal version of Problem 1** — a grouped-count-by-issue-type table with an SLA-breach flag over the tickets sheet, for the internal ops side the brief also asks about. Left out under this timeline per the spec's locked scope decision, but it's the most natural next increment since it reuses the same structured-data layer.
3. **Real authentication** in place of the account-switcher dropdown, once there's an actual identity provider to bind to — the access-control logic underneath doesn't change, just where `account_id` gets resolved from.
4. **Confidence surfacing in the UI**, not just in the agent's text — e.g. a visible badge when an answer leans on a historical ticket or an ambiguous-conflict case, so escalation-worthy answers are visually distinct from confidently-sourced ones.

## What was intentionally left out

- **Internal ops chatbot / dual user-context support** — the brief allows building either side; the customer-facing agent is where access control and multi-step reasoning are most demonstrable.
- **Problem 1 (Proactive Issue Detection)** — a real version needs an aggregation/anomaly view built from a ticket volume large enough to show trends; the assessment's 7-ticket dataset doesn't support a meaningful demo of that.
- **Multi-agent orchestration** — the task is sequential tool use by one reasoner; splitting it across agents would add coordination complexity without solving a problem this scope has.
- **Real authentication** — explicitly allowed to be mocked by the brief.
- **A production database / vector store** — the dataset is small enough that pandas + TF-IDF are the right-sized tools; see the architecture note's trade-offs section.

## One metric to judge usefulness

**Percentage of customer queries resolved without escalation, while maintaining 0% failures on the trap-test set.** Resolution rate alone is a hollow metric — a system that resolves 95% of queries by confidently guessing is worse than one that resolves 70% and escalates the rest correctly. Pairing the resolution rate with a hard trust-check floor is what actually predicts whether customer operations would trust the system enough to let it handle real traffic.
