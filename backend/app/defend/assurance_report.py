"""
Full Red-Team Assurance Report -- the exportable artifact, not just a
dashboard view. Combines:
  - the red-teaming audit (redteam_audit.py, RBI FREE-AI Rec 20 aligned)
  - fidelity measurements per specialist (generate/fidelity.py)
  - false-positive-rate / operating-point data (model_store, auto_specialist)
  - newly-discovered-pattern history (taxonomy_store)
  - session-scoped model version identifiers

...into one document intended to be handed to a bank's risk/security/
governance function, per the reviewer's suggestion that persistent
scoreboard history should become "audit evidence," not just a dashboard.

REQUIRED DISCLAIMER (included verbatim in every generated report, and
rendered in the UI, not just here): this report is a technical evidence
artifact, not a compliance certification or legal opinion. See DISCLAIMER
below for exact wording -- don't paraphrase it away in the UI or a deck.

HONEST SCOPE NOTE: model version identifiers here are session-scoped
counters ("session-v2" = trained twice since the server last started),
not durable MLOps versioning (no artifact registry, no persistent
version history across restarts). A production version of this needs a
real model registry; this reports what actually exists today rather than
implying more rigor than there is.
"""
import uuid
from datetime import datetime, timezone

from app.taxonomy import taxonomy_store
from app.defend import redteam_audit
from app.defend.model_store import model_store
from app.defend.auto_specialist import auto_specialist_store
from app.generate import tabular_generator
from app.generate import fidelity as fidelity_module

DISCLAIMER = (
    "This report is a technical red-team evidence artifact. It does not constitute an RBI "
    "compliance certification or legal opinion. Orion operationalizes RBI FREE-AI Committee "
    "Report Recommendation 20 (\"Red Teaming\", Protection pillar, published 13 August 2025) -- "
    "it does not claim to make any institution compliant with that or any other recommendation. "
    "Model version identifiers below are session-scoped counters, not durable MLOps versioning."
)


def _model_version(attack_id: str, tier: str) -> str:
    if attack_id == "account_takeover":
        return model_store.model_version("account_takeover")
    if tier == "auto":
        return auto_specialist_store.model_version(attack_id)
    return "n/a (hybrid Groq/rule-based specialist, no single versioned model)"


def generate_report(rounds_per_attack: int = 3) -> dict:
    audit = redteam_audit.run_audit(rounds_per_attack=rounds_per_attack)
    entries = {e["attack_id"]: e for e in taxonomy_store.all()}
    discovered = [e for e in entries.values() if e.get("seed_or_discovered") == "discovered"]

    fidelity_results = {}
    for attack_id, entry in entries.items():
        try:
            reference = tabular_generator.generate(attack_id, n=200, seed=101, taxonomy_entry=entry)
            synth = tabular_generator.generate(attack_id, n=200, seed=202, taxonomy_entry=entry)
            fidelity_results[attack_id] = fidelity_module.score_fidelity(reference, synth)
        except Exception as e:  # noqa: BLE001 -- a fidelity failure for one entry shouldn't kill the whole report
            fidelity_results[attack_id] = {"error": str(e)}

    fpr_summary = {}
    for attack_id, m in model_store.last_training_metrics.items():
        if "false_positive_rate_on_legit" in m:
            fpr_summary[attack_id] = m["false_positive_rate_on_legit"]
    for attack_id, m in auto_specialist_store.metrics.items():
        if "false_positive_rate_on_legit" in m:
            fpr_summary[attack_id] = m["false_positive_rate_on_legit"]

    scored = [s for s in audit["per_specialist"] if s["blue_win_rate"] is not None]
    worst_performers = sorted(scored, key=lambda x: x["blue_win_rate"])[:3]

    versioned_specialists = [
        {
            "attack_id": s["attack_id"],
            "display_name": s["display_name"],
            "tier": s["tier"],
            "model_version": _model_version(s["attack_id"], s["tier"]),
            "blue_win_rate": s["blue_win_rate"],
            "false_positive_rate_on_legit": fpr_summary.get(s["attack_id"]),
            "fidelity_score": (fidelity_results.get(s["attack_id"]) or {}).get("fidelity_score"),
        }
        for s in audit["per_specialist"]
    ]

    return {
        "report_id": uuid.uuid4().hex[:12],
        "title": f"Red-Team Assurance Report — {datetime.now(timezone.utc).strftime('%B %Y')}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
        "regulatory_basis": audit["regulatory_basis"],
        "summary": {
            "attack_families_tested": audit["specialists_audited"],
            "attack_families_excluded": audit["specialists_excluded"],
            "rounds_conducted": audit["total_rounds_scored"],
            "overall_blue_win_rate": audit["overall_blue_win_rate"],
            "newly_discovered_patterns_this_session": len(discovered),
        },
        "per_specialist": versioned_specialists,
        "worst_performing_specialists": worst_performers,
        "newly_discovered_patterns": [
            {
                "attack_id": d["attack_id"],
                "display_name": d["display_name"],
                "created_at": d.get("created_at"),
                "promoted_at": d.get("promoted_at"),
                "research_source_count": len(d.get("research_sources", [])),
            }
            for d in discovered
        ],
        "fidelity_measurements": fidelity_results,
        "methodology": audit["methodology"],
    }
