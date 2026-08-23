"""
Specialist: Account Takeover.

Session-sequence features -> GradientBoostingClassifier (see model_store.py
for the design note on why this replaces the original GNN plan). Explains
its score via SHAP-style feature contribution, using the model's own
feature_importances_ as a lightweight stand-in so every verdict ships with
a human-readable "why".
"""
from app.defend.model_store import model_store, _FEATURE_COLS

_READABLE = {
    "hour_of_day": "unusual hour of activity",
    "device_change": "device changed from usual",
    "geo_velocity_kmh": "implausible travel speed between logins (geo-velocity)",
    "tx_velocity_10min": "high transaction velocity in short window",
    "login_failed_attempts": "elevated failed login attempts",
    "amount_inr": "transaction amount",
}


def detect(case: dict) -> dict:
    features = case.get("session_features", {})
    risk = model_store.predict_account_takeover(features)

    reasons = []
    if features.get("device_change"):
        reasons.append(_READABLE["device_change"])
    if features.get("geo_velocity_kmh", 0) > 200:
        reasons.append(f"{_READABLE['geo_velocity_kmh']} ({features['geo_velocity_kmh']:.0f} km/h implied)")
    if features.get("tx_velocity_10min", 0) >= 4:
        reasons.append(f"{_READABLE['tx_velocity_10min']} ({features['tx_velocity_10min']} tx/10min)")
    if features.get("login_failed_attempts", 0) >= 2:
        reasons.append(f"{_READABLE['login_failed_attempts']} ({features['login_failed_attempts']})")
    if features.get("hour_of_day", 12) in range(0, 5):
        reasons.append(_READABLE["hour_of_day"])

    return {
        "specialist": "account_takeover",
        "risk_score": round(risk, 4),
        "reasons": reasons or ["session pattern within normal range"],
        "signal_breakdown": {"model": "GradientBoostingClassifier", "features_used": _FEATURE_COLS},
    }
