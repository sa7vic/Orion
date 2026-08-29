"""
Generalist detector -- broad IsolationForest anomaly detector trained
across every taxonomy entry's synthetic feature space (see model_store.py).

Two roles:
1. Fallback: runs whenever the router's confidence is below threshold.
2. Novelty sensor: ALSO runs in parallel on every case (cheap -- it's a
   sklearn IsolationForest, not an LLM call), so we can compare "did a
   specialist claim this" vs "did the generalist flag it anyway". A
   pattern of generalist-flags-but-no-specialist-claims feeds the
   feedback loop.
"""
from app.defend.model_store import model_store
from app.defend.feature_utils import extract_features


def detect(case: dict) -> dict:
    features = extract_features(case)
    risk, is_anomaly = model_store.predict_generalist(features)
    reasons = []
    if is_anomaly:
        reasons.append("flagged as statistical anomaly relative to all known fraud/legit patterns")
    else:
        reasons.append("within normal statistical range across all known patterns")
    return {
        "specialist": "generalist",
        "risk_score": round(risk, 4),
        "is_anomaly": is_anomaly,
        "reasons": reasons,
        "signal_breakdown": {"model": "IsolationForest", "role": "fallback_and_novelty_sensor"},
    }
