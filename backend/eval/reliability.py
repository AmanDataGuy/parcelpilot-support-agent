"""pass^k reliability runner: does the agent get each trap case right k
times running, not just once? Adapted from the pass^k idea in Resolv's eval
suite — simplified to "all k repeats passed" rather than the combinatorial
C(c,k)/C(n,k) estimator, since this runs exactly k trials per case rather
than subsampling k from a larger pool of n.

ponytail: no eval framework, argparse + a loop is the whole "runner".

Usage, from backend/ with GEMINI_API_KEY set:
    python -m eval.reliability --k 3
"""
import argparse

from app import agent
from eval.cases import TRAP_CASES


def _run_once(case) -> bool:
    messages = [{"role": "user", "parts": [{"text": case.question}]}]
    updated, trace = agent.run_turn(messages, account_id=case.account_id)
    reply = "\n".join(p.text for p in updated[-1]["parts"] if getattr(p, "text", None))
    return case.check(reply, trace)


def main() -> None:
    parser = argparse.ArgumentParser(description="pass^k reliability sweep over the trap-question set")
    parser.add_argument("--k", type=int, default=3, help="repeats per case")
    args = parser.parse_args()

    print(f"Running {len(TRAP_CASES)} cases x {args.k} repeats = {len(TRAP_CASES) * args.k} live calls\n")

    case_passed_all_k = []
    for case in TRAP_CASES:
        outcomes = [_run_once(case) for _ in range(args.k)]
        passed_all_k = all(outcomes)
        case_passed_all_k.append(passed_all_k)
        outcome_str = "".join("P" if o else "F" for o in outcomes)
        print(f"{case.name:45s} {outcome_str}  {'PASS^k' if passed_all_k else 'FAIL'}")

    pass_k = sum(case_passed_all_k) / len(case_passed_all_k)
    print(
        f"\npass^{args.k} = {pass_k:.3f} "
        f"({sum(case_passed_all_k)}/{len(case_passed_all_k)} cases passed all {args.k} repeats)"
    )


if __name__ == "__main__":
    main()
