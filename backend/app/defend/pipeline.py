"""
The one place "what happens when a case comes in" is defined. Used by
/api/detect directly, and by adversarial.py's evolution loop (round 1 and
round 2 both go through this exact same function) -- if this drifted into
two copies, an "improvement" in one path could silently stop applying to
the other.
"""
import uuid
from datetime import datetime, timezone

from app.taxonomy import taxonomy_store
from app.defend.router import router as case_router
from app.defend import generalist, registry, policy


def summarize_case(case: dict, channel: str | None) -> str:
    if "transcript" in case:
        return case["transcript"][:400]
    if "vpa" in case or "app_package" in case:
        return f"vpa={case.get('vpa')} app_package={case.get('app_package')} channel={channel}"
    if "application_fields" in case:
        return f"KYC case: {case.get('application_fields')} vs {case.get('document_fields')}"
    if "session_features" in case:
        return f"session case: {case['session_features']} channel={channel}"
    return str(case)[:400]


def run_detection(case: dict, channel: str | None, summary: str | None = None) -> dict:
    case = dict(case)
    case.setdefault("summary", summary or summarize_case(case, channel))
    summary = case["summary"]

    routing = case_router.route(summary, declared_channel=channel)
    gen_result = generalist.detect(case)

    specialist_result = None
    if routing["attack_id"]:
        entry = taxonomy_store.get(routing["attack_id"])
        specialist_result = registry.run_specialist(entry, case)

    top_specialist_score = specialist_result["risk_score"] if specialist_result else 0.0
    final_score = max(top_specialist_score, gen_result["risk_score"])
    all_reasons = (specialist_result["reasons"] if specialist_result else []) + gen_result["reasons"]
    policy_decision = policy.decide(final_score)

    return {
        "case_id": str(uuid.uuid4())[:8],
        "channel": channel,
        "summary": summary,
        "routing": routing,
        "specialist_result": specialist_result,
        "generalist_result": gen_result,
        "final_risk_score": round(final_score, 4),
        "final_reasons": all_reasons,
        "risk_tier": "high" if final_score >= 0.7 else "medium" if final_score >= 0.4 else "low",
        "policy": policy_decision,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "_case": case,  # kept for callers (e.g. adversarial.py) that need the raw case; stripped before returning to the client
    }


def strip_internal(verdict: dict) -> dict:
    return {k: v for k, v in verdict.items() if not k.startswith("_")}
