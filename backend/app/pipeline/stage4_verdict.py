"""
STAGE 4 — Verdict Aggregation
Input:  the job's rules (with rule_type hard/soft) + Stage 3's ruleResults.
Output: { verdict: eligible|semi_eligible|not_eligible, confidence: int }

This stage is intentionally deterministic (no LLM call) so that the final
eligible/not_eligible decision is always explainable and reproducible from
the evidence Stage 3 produced — the AI does the judgement-heavy evidence
gathering, this stage just applies IHMCL's decision policy consistently.

Policy:
  - Any HARD rule with status 'failed'                -> not_eligible
  - Any HARD rule 'unverified' / 'missing_document'    -> semi_eligible (needs human review)
  - All HARD rules 'passed', regardless of soft rules  -> eligible
  - No hard rules configured at all                    -> semi_eligible (nothing to auto-decide)
"""


def run(rules: list[dict], rule_results: list[dict]) -> dict:
    if not rules:
        return {"verdict": "semi_eligible", "confidence": 30}

    by_text = {r["rule"]: r for r in rule_results}
    hard_rules = [r for r in rules if r.get("rule_type") == "hard"]

    if not hard_rules:
        return {"verdict": "semi_eligible", "confidence": 40}

    failed = 0
    unverified = 0
    passed = 0

    for rule in hard_rules:
        res = by_text.get(rule["rule_text"])
        status = res["status"] if res else "unverified"
        if status == "failed":
            failed += 1
        elif status in ("unverified", "missing_document"):
            unverified += 1
        elif status == "passed":
            passed += 1

    total = len(hard_rules)

    if failed > 0:
        verdict = "not_eligible"
        confidence = min(95, 60 + int(40 * failed / total))
    elif unverified > 0:
        verdict = "semi_eligible"
        confidence = max(30, int(70 * passed / total))
    else:
        verdict = "eligible"
        confidence = 90

    return {"verdict": verdict, "confidence": confidence}
