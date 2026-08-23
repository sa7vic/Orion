"""
Red-Team Audit Report -- Orion's "Assure" stage.

This is a working implementation of a SPECIFIC, NAMED recommendation from
a real, current regulatory framework -- not an invented certification
scheme, and NOT a claim that using this tool makes anyone compliant with
anything. The Reserve Bank of India's FREE-AI Committee Report (published
13 August 2025 -- "Framework for Responsible and Ethical Enablement of
Artificial Intelligence") contains, under its "Protection" pillar:

    Recommendation 20 -- "Red Teaming" (Protection, Medium term):
    "Set up structured red teaming across [the] AI lifecycle, proportionate
    to risk -- more frequent for high-risk models. Include trigger-based
    [red teaming] for evolving threats."

A separate recommendation, Recommendation 24 (AI Audit Framework), calls
for periodic, independent, risk-tiered audits of AI models. This module
generates evidence that could support BOTH -- structured, timestamped,
repeatable red-teaming records (Rec 20) with full retained detail suitable
for an audit trail (Rec 24) -- without claiming to BE either recommendation
fulfilled. Verified against multiple independent secondary sources (CISO
analysis, legal/compliance commentary, industry summaries) describing the
same recommendation number and wording; not read against RBI's primary PDF
directly -- verify exact wording there before citing in a formal
submission.

IMPORTANT WORDING DISCIPLINE: this is a *committee report recommendation*,
not a binding RBI regulation or mandate. Say "operationalizes
Recommendation 20" -- never "satisfies an RBI mandate" or "makes you
compliant." Orion is not an auditor; it generates evidence a regulated
entity's own governance process would use.

WHAT THIS DELIBERATELY DOES NOT DO: assign a letter grade, a star rating,
or any other invented scale. An earlier version of this module did that
and it was correctly called out as "made up out of thin air" -- there is
no published industry standard for grading fraud-model adversarial
robustness, so this reports the real, measured numbers (blue win rate,
per-specialist breakdown, full round-level detail) and nothing else.
Interpreting what counts as an acceptable win rate is a risk-appetite
decision for the regulated entity's own board/governance process, per
FREE-AI's own model -- not something this tool should presume to grade.
"""
import threading
import uuid
from datetime import datetime, timezone

from app.taxonomy import taxonomy_store
from app.defend import adversarial

_lock = threading.Lock()
_history: list[dict] = []

REGULATORY_BASIS = {
    "framework": "RBI FREE-AI Committee Report",
    "full_name": "Framework for Responsible and Ethical Enablement of Artificial Intelligence",
    "published": "2025-08-13",
    "status": "Committee report recommendation, NOT a binding RBI regulation or mandate.",
    "primary_recommendation": {
        "number": 20,
        "title": "Red Teaming",
        "pillar": "Protection",
        "term": "Medium term",
        "text": "Set up structured red teaming across the AI lifecycle, proportionate to risk -- "
                "more frequent for high-risk models. Include trigger-based red teaming for evolving threats.",
    },
    "related_recommendation": {
        "number": 24,
        "title": "AI Audit Framework",
        "text": "Periodic, independent, risk-tiered audits of AI models -- Orion's retained "
                "round-level detail is structured to support this, not to replace it.",
    },
    "orion_claim": (
        "Orion operationalizes Recommendation 20's structured and trigger-based red-teaming "
        "concept, and generates evidence in a shape that could support a Recommendation 24 audit "
        "process. It does not claim to make any institution compliant with either recommendation."
    ),
    "source_note": "Verified against multiple independent secondary sources (CISO/compliance "
                    "commentary, legal analysis, industry summaries) citing the same recommendation "
                    "number and wording -- not checked against RBI's primary PDF directly. Verify "
                    "there before citing in a formal submission.",
}

# fake_app_qr_substitution is a deterministic registry check -- mutation
# isn't a meaningful concept for it (see adversarial.py), so it's
# excluded from the audit battery rather than contributing a misleading
# "0 rounds scored" entry.
_EXCLUDED_FROM_AUDIT = {"fake_app_qr_substitution"}


def run_audit(rounds_per_attack: int = 3) -> dict:
    entries = [e for e in taxonomy_store.all() if e["attack_id"] not in _EXCLUDED_FROM_AUDIT]

    per_specialist = []
    total_red_wins = 0
    total_scored = 0

    for entry in entries:
        battle = adversarial.run_battle(entry["attack_id"], rounds=rounds_per_attack)
        per_specialist.append({
            "attack_id": entry["attack_id"],
            "display_name": entry["display_name"],
            "tier": entry.get("specialist_tier", "auto"),
            "rounds_scored": battle["rounds_scored"],
            "red_wins": battle["red_wins"],
            "blue_wins": battle["blue_wins"],
            "blue_win_rate": round(battle["blue_wins"] / battle["rounds_scored"], 3) if battle["rounds_scored"] else None,
            # Full round-level detail retained for the audit log, per
            # FREE-AI's "logging and record retention for auditability".
            "round_detail": battle["rounds"],
        })
        total_red_wins += battle["red_wins"]
        total_scored += battle["rounds_scored"]

    overall_blue_win_rate = round((total_scored - total_red_wins) / total_scored, 3) if total_scored else None

    report = {
        "audit_id": uuid.uuid4().hex[:12],
        "conducted_at": datetime.now(timezone.utc).isoformat(),
        "regulatory_basis": REGULATORY_BASIS,
        "rounds_per_specialist": rounds_per_attack,
        "specialists_audited": len(entries),
        "specialists_excluded": list(_EXCLUDED_FROM_AUDIT),
        "total_rounds_scored": total_scored,
        "overall_blue_win_rate": overall_blue_win_rate,
        "per_specialist": sorted(
            per_specialist,
            key=lambda x: (x["blue_win_rate"] is None, x["blue_win_rate"] or 0),
        ),
        "methodology": (
            f"{len(entries)} specialists, {rounds_per_attack} adversarial rounds each "
            "(generate attack -> detect -> mutate to evade -> detect again). "
            "overall_blue_win_rate = (scored rounds where detection held) / (total scored rounds). "
            "Rounds where round 1 wasn't caught, or no mutation strategy exists for that case shape, "
            "are excluded from the denominator -- not counted as either side winning. No letter grade "
            "or pass/fail threshold is applied; interpreting the win rate against risk appetite is "
            "left to the regulated entity's own governance process, per FREE-AI's model."
        ),
    }

    with _lock:
        _history.append(report)

    return report


def get_history_summary() -> list[dict]:
    """Lightweight list for trend views -- 'is the defense getting harder
    to beat over successive audits' -- without the full per-round detail."""
    with _lock:
        return [
            {
                "audit_id": r["audit_id"],
                "conducted_at": r["conducted_at"],
                "overall_blue_win_rate": r["overall_blue_win_rate"],
                "total_rounds_scored": r["total_rounds_scored"],
            }
            for r in _history
        ]


def get_latest() -> dict | None:
    with _lock:
        return _history[-1] if _history else None


def get_by_id(audit_id: str) -> dict | None:
    with _lock:
        for r in _history:
            if r["audit_id"] == audit_id:
                return r
        return None


def reset():
    with _lock:
        _history.clear()
