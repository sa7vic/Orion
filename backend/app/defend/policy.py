"""
Policy engine: turns a risk score into an action a payment system would
actually take. Detection alone isn't mitigation -- the challenge brief
explicitly asks for "detects, flags, and mitigates."

Thresholds are deliberately simple and visible (not learned) because a
policy layer that a compliance team can read and audit in one glance is
worth more here than a marginal accuracy gain from a learned threshold --
this is exactly the kind of decision a real deployment would want to be
able to explain to a regulator.
"""

POLICY_THRESHOLDS = [
    (0.85, "BLOCK", "Risk too high to proceed automatically -- transaction blocked, case queued for manual review."),
    (0.60, "STEP_UP", "Elevated risk -- require additional authentication (e.g. biometric or app-based OTP) before proceeding."),
    (0.25, "MONITOR", "Below action threshold but logged for pattern monitoring; no friction added for the user."),
    (0.0, "ALLOW", "Low risk -- transaction proceeds normally."),
]


def decide(risk_score: float) -> dict:
    for threshold, action, rationale in POLICY_THRESHOLDS:
        if risk_score >= threshold:
            return {"action": action, "rationale": rationale, "threshold_crossed": threshold}
    return {"action": "ALLOW", "rationale": "Low risk.", "threshold_crossed": 0.0}
