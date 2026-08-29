"""
Governance lifecycle for auto-discovered specialists: Discovered -> Shadow
-> Promoted (or stays Shadow if it fails the gate).

WHY THIS EXISTS: every review of this project independently raised the
same question -- "what if an auto-discovered specialist is garbage? Does
it just go live?" Before this module, the answer was yes: feedback_loop's
_promote() trained a classifier and immediately treated it as a fully
active, routable specialist. That's not how a real institution would (or
should) deploy an automatically-generated fraud model.

THE GATE (illustrative prototype thresholds, NOT a risk-committee-defined
production standard -- say so explicitly if this comes up):
  - precision >= 0.60
  - recall    >= 0.60
  - false_positive_rate_on_legit <= 0.35
  - adversarial: must survive at least half of a quick 3-round red-team
    battle (blue_win_rate >= 0.5), using the SAME adversarial.py mechanism
    the rest of this project uses -- not a separate, softer check.

A newly-discovered pattern that passes all four gets lifecycle_stage
"promoted" and becomes routable (router.py only routes live traffic to
"promoted" entries). One that fails stays "shadow": visible in the roster
and taxonomy for inspection, its model is trained and its metrics are
real, but the router will NOT send live cases to it -- exactly what
"shadow deployment" means in real MLOps, not a euphemism for "hidden."

WHAT THIS DOES NOT DO: retry training, auto-tune the gate, or notify a
human. A real system needs a "someone gets paged when a shadow specialist
fails the gate" step; this prototype logs the failure reasons onto the
taxonomy entry itself, which is enough for a demo but not enough for
production incident response.
"""
from app.defend import adversarial

GATE_CRITERIA = {
    "min_precision": 0.60,
    "min_recall": 0.60,
    "max_false_positive_rate": 0.35,
    "min_adversarial_blue_win_rate": 0.50,
    "adversarial_rounds": 3,
}


def evaluate_gate(attack_id: str, train_metrics: dict) -> dict:
    reasons_failed = []

    precision = train_metrics.get("precision", 0.0)
    recall = train_metrics.get("recall", 0.0)
    fpr = train_metrics.get("false_positive_rate_on_legit", 1.0)

    if precision < GATE_CRITERIA["min_precision"]:
        reasons_failed.append(f"precision {precision:.3f} below gate minimum {GATE_CRITERIA['min_precision']}")
    if recall < GATE_CRITERIA["min_recall"]:
        reasons_failed.append(f"recall {recall:.3f} below gate minimum {GATE_CRITERIA['min_recall']}")
    if fpr > GATE_CRITERIA["max_false_positive_rate"]:
        reasons_failed.append(f"false positive rate {fpr:.3f} above gate maximum {GATE_CRITERIA['max_false_positive_rate']}")

    battle = adversarial.run_battle(attack_id, rounds=GATE_CRITERIA["adversarial_rounds"])
    blue_win_rate = (
        round(battle["blue_wins"] / battle["rounds_scored"], 3) if battle["rounds_scored"] else None
    )
    if blue_win_rate is None:
        reasons_failed.append(
            "adversarial battle produced no scored rounds (round 1 was never caught) -- "
            "cannot confirm this specialist detects its own attack type at all"
        )
    elif blue_win_rate < GATE_CRITERIA["min_adversarial_blue_win_rate"]:
        reasons_failed.append(
            f"adversarial blue win rate {blue_win_rate:.3f} below gate minimum "
            f"{GATE_CRITERIA['min_adversarial_blue_win_rate']} ({battle['blue_wins']}W-{battle['red_wins']}L)"
        )

    passed = len(reasons_failed) == 0

    return {
        "passed": passed,
        "lifecycle_stage": "promoted" if passed else "shadow",
        "criteria": GATE_CRITERIA,
        "measured": {
            "precision": precision,
            "recall": recall,
            "false_positive_rate": fpr,
            "adversarial_blue_win_rate": blue_win_rate,
            "adversarial_rounds_scored": battle["rounds_scored"],
        },
        "reasons_failed": reasons_failed,
    }
