"""
Shared feature contract. Every risk-scoring module (generalist,
account_takeover, auto_specialist) needs to turn an arbitrary incoming
`case` dict into the same 6-column numeric feature vector, since
model_store's models and the synthetic generator both key off these
columns. Centralized here so there's exactly one definition of "how do we
turn a vishing call / QR scan / KYC submission / session event into
features" instead of three slightly-different copies drifting apart.
"""

FEATURE_COLS = ["hour_of_day", "device_change", "geo_velocity_kmh",
                 "tx_velocity_10min", "login_failed_attempts", "amount_inr"]

# Legit baseline (mirrors tabular_generator.FEATURE_PROFILES["legit"]) used
# to explain *why* a feature looks anomalous in plain language.
LEGIT_BASELINE = {
    "hour_of_day": {"mean": 14, "std": 4},
    "device_change": {"mean": 0.03, "std": 0.17},
    "geo_velocity_kmh": {"mean": 5, "std": 8},
    "tx_velocity_10min": {"mean": 1, "std": 0.8},
    "login_failed_attempts": {"mean": 0.1, "std": 0.3},
    "amount_inr": {"mean": 1500, "std": 2200},
}

READABLE_FEATURE_NAMES = {
    "hour_of_day": "unusual hour of activity",
    "device_change": "device changed from usual",
    "geo_velocity_kmh": "implausible travel speed between logins (geo-velocity)",
    "tx_velocity_10min": "high transaction velocity in short window",
    "login_failed_attempts": "elevated failed login attempts",
    "amount_inr": "transaction amount deviates from typical range",
}


def extract_features(case: dict) -> dict:
    """Best-effort feature extraction for ANY case shape -- explicit
    session_features win if present (account-takeover cases), otherwise
    infer from whatever metadata or top-level attributes the case carries
    (vishing/QR/KYC/stub cases all carry metadata)."""
    if "session_features" in case:
        feats = case["session_features"]
    else:
        metadata = case.get("metadata", {})
        feats = {
            "hour_of_day": metadata.get("hour_of_day", case.get("hour_of_day", 12)),
            "device_change": int(bool(metadata.get("voip_masked") or metadata.get("device_change") or case.get("device_change"))),
            "geo_velocity_kmh": metadata.get("geo_velocity_kmh", case.get("geo_velocity_kmh", 5)),
            "tx_velocity_10min": metadata.get("tx_velocity_10min", case.get("tx_velocity_10min", 1)),
            "login_failed_attempts": metadata.get("login_failed_attempts", case.get("login_failed_attempts", 0)),
            "amount_inr": case.get("amount_inr", metadata.get("amount_inr", 1000)),
        }
    return {c: feats.get(c, 0) for c in FEATURE_COLS}


def explain_deviation(features: dict, max_reasons: int = 3) -> list[str]:
    """Compare features against the legit baseline and return
    human-readable reasons for the features that deviate most (in z-score
    terms) -- this is what lets an auto-trained model explain itself
    without needing SHAP or a hand-written rule per attack type."""
    scored = []
    for feat, val in features.items():
        baseline = LEGIT_BASELINE.get(feat)
        if not baseline or baseline["std"] == 0:
            continue
        z = abs(val - baseline["mean"]) / baseline["std"]
        scored.append((z, feat, val))
    scored.sort(reverse=True)
    reasons = []
    for z, feat, val in scored[:max_reasons]:
        if z >= 1.2:
            reasons.append(f"{READABLE_FEATURE_NAMES.get(feat, feat)} ({val:.1f}, z={z:.1f})")
    return reasons
