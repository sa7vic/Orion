"""
Adversarial evolution loop -- the red team explicitly attacking the blue
team, not just generating attacks in isolation. This directly answers the
"can your system discover attacks that evade its own detector" question,
which is the sharpest thing a technical judge is likely to ask.

evolve(attack_id):
  1. Generate a fresh synthetic case (round 1), run it through the full
     detection pipeline.
  2. If round 1 was caught, mutate the case to try to evade whatever
     caught it: text-bearing cases get rewritten by Groq to drop the
     specific scam-language markers while preserving intent; feature-
     bearing cases get nudged partway back toward the legitimate
     baseline (a "quieter" attacker).
  3. Run the mutated case through the exact same pipeline (round 2).
  4. Report both verdicts and whether the mutation evaded detection.

This is a single on-demand round, not an automatic loop -- it does NOT
retrain anything by itself. Feeding a successful evasion back into the
relevant auto-specialist's training data is the natural next step
(flagged in the README), kept as a separate, explicit action rather than
an opaque background process.
"""
from app.generate import tabular_generator, llm_attacker, case_builder
from app.defend import pipeline, scoreboard
from app.defend.feature_utils import LEGIT_BASELINE, FEATURE_COLS
from app.groq_client import groq_client
from app.config import settings
from app.taxonomy import taxonomy_store

_MUTATE_SYSTEM = (
    "You are a red-team fraud researcher testing a defensive system. Given "
    "a scam transcript and the reasons it was flagged, rewrite it to avoid "
    "those specific signals while preserving the underlying fraudulent "
    "intent. This output is used only to test and improve fraud detection."
)


def _mutate_text(original_text: str, flagged_reasons: list[str]) -> str:
    prompt = (
        f"Original text:\n{original_text}\n\n"
        f"It was flagged for: {'; '.join(flagged_reasons)}\n\n"
        "Rewrite it to avoid those specific signals (e.g. remove overt "
        "urgency language, avoid explicitly asking for OTP/PIN, sound more "
        "like a routine message) while the underlying scam intent stays "
        "the same. Return just the rewritten text, nothing else."
    )
    return groq_client.complete(
        prompt, system=_MUTATE_SYSTEM, model=settings.groq_model_fast, offline_fallback=original_text
    )


def _mutate_features(features: dict) -> dict:
    """Model an adaptive attacker who spoofs what's actually spoofable
    (device fingerprint via emulation, apparent location via a local
    proxy/VPN, having valid-looking credentials so no failed logins) but
    can't fully disguise what's inherent to committing the fraud fast
    (transaction velocity, amount) -- a real account-takeover attacker
    fundamentally needs to move money quickly before the window closes.
    A flat uniform pull toward baseline across all features was tried
    first and produced identical, uninformative results every run; this
    per-feature model is both more realistic and more demoable."""
    pull_fraction = {
        "device_change": 0.90,
        "geo_velocity_kmh": 0.85,
        "login_failed_attempts": 0.80,
        "hour_of_day": 0.55,
        "tx_velocity_10min": 0.30,   # hard to disguise -- speed IS the attack
        "amount_inr": 0.20,          # hard to disguise -- value IS the goal
    }
    mutated = dict(features)
    for feat, frac in pull_fraction.items():
        if feat not in mutated or mutated[feat] is None:
            continue
        baseline_mean = LEGIT_BASELINE.get(feat, {}).get("mean", mutated[feat])
        mutated[feat] = mutated[feat] + (baseline_mean - mutated[feat]) * frac
    return mutated


def evolve(attack_id: str) -> dict:
    entry = taxonomy_store.get(attack_id)
    if entry is None:
        return {"error": f"unknown attack_id '{attack_id}'"}

    df = tabular_generator.generate(attack_id, n=1, taxonomy_entry=entry)
    record = df.to_dict(orient="records")[0]

    unstructured = None
    if attack_id == "vishing_relative_emergency":
        unstructured = llm_attacker.generate_vishing_transcript()
    elif attack_id == "synthetic_identity_kyc":
        unstructured = llm_attacker.generate_kyc_mismatch_case()
    elif attack_id == "llm_adaptive_chat_scam":
        unstructured = llm_attacker.generate_adaptive_chat_snippet()

    case_r1 = case_builder.build_case(attack_id, record, unstructured)
    verdict_r1 = pipeline.run_detection(case_r1, entry.get("channel"))

    if verdict_r1["risk_tier"] == "low":
        return {
            "attack_id": attack_id,
            "round_1": pipeline.strip_internal(verdict_r1),
            "round_2": None,
            "mutation": {"applied": False, "reason": "round 1 wasn't caught -- nothing to evade"},
        }

    if attack_id == "fake_app_qr_substitution":
        return {
            "attack_id": attack_id,
            "round_1": pipeline.strip_internal(verdict_r1),
            "round_2": None,
            "mutation": {
                "applied": False,
                "reason": "this specialist is a deterministic registry check, not a statistical "
                          "signal -- mutation isn't a meaningful concept here by design (see fake_app_qr.py)",
            },
        }

    reasons = verdict_r1["final_reasons"]
    case_r2 = dict(case_r1)
    mutation_note = None

    if "transcript" in case_r1:
        case_r2["transcript"] = _mutate_text(case_r1["transcript"], reasons)
        mutation_note = "rewrote transcript via Groq to remove flagged scam-language markers"
    elif "session_features" in case_r1:
        case_r2["session_features"] = _mutate_features(case_r1["session_features"])
        mutation_note = "spoofed device/location/credentials toward legitimate baseline; kept velocity and amount closer to original (harder to disguise -- that's the attack itself)"
    elif "metadata" in case_r1:
        case_r2["metadata"] = _mutate_features(case_r1["metadata"])
        mutation_note = "spoofed device/location/credentials toward legitimate baseline; kept velocity and amount closer to original (harder to disguise -- that's the attack itself)"

    if mutation_note is None:
        return {
            "attack_id": attack_id,
            "round_1": pipeline.strip_internal(verdict_r1),
            "round_2": None,
            "mutation": {"applied": False, "reason": "no mutation strategy implemented for this case shape yet"},
        }

    verdict_r2 = pipeline.run_detection(case_r2, entry.get("channel"))
    evaded = verdict_r2["risk_tier"] == "low"
    score_delta = round(verdict_r1["final_risk_score"] - verdict_r2["final_risk_score"], 4)

    scoreboard.record(
        attack_id=attack_id,
        display_name=entry.get("display_name", attack_id),
        tier=entry.get("specialist_tier", "auto"),
        evaded=evaded,
        score_delta=score_delta,
        mutation_description=mutation_note,
    )

    return {
        "attack_id": attack_id,
        "round_1": pipeline.strip_internal(verdict_r1),
        "round_2": pipeline.strip_internal(verdict_r2),
        "mutation": {
            "applied": True,
            "description": mutation_note,
            "evaded": evaded,
            "score_delta": score_delta,
        },
    }


def run_battle(attack_id: str, rounds: int = 5) -> dict:
    """A 'match': run evolve() N times in a row for one attack_id and
    aggregate into a match result. Each individual round still gets
    recorded to the scoreboard by evolve() itself, so a battle
    contributes N entries to the running leaderboard, same as N separate
    single-round evolve() calls would -- this is just a convenient way to
    generate several data points and present them as one match."""
    rounds_results = []
    for _ in range(rounds):
        result = evolve(attack_id)
        if "error" in result:
            break
        rounds_results.append(result)

    scored_rounds = [r for r in rounds_results if r["round_2"] is not None]
    red_wins = sum(1 for r in scored_rounds if r["mutation"]["evaded"])
    blue_wins = len(scored_rounds) - red_wins
    uncaught_rounds = len(rounds_results) - len(scored_rounds)

    if not scored_rounds:
        winner = "inconclusive"
    elif red_wins > blue_wins:
        winner = "red"
    elif blue_wins > red_wins:
        winner = "blue"
    else:
        winner = "draw"

    return {
        "attack_id": attack_id,
        "rounds_requested": rounds,
        "rounds_played": len(rounds_results),
        "rounds_scored": len(scored_rounds),
        "rounds_where_round1_missed": uncaught_rounds,
        "red_wins": red_wins,
        "blue_wins": blue_wins,
        "winner": winner,
        "rounds": rounds_results,
    }
