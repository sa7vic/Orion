"""
Threshold analysis for any model that exposes predict_proba over the
standard FEATURE_COLS (account_takeover's GBM, and every auto-tier
LogisticRegression). Turns "this detector has a 15.79% FPR" from a fixed
fact into what it actually is: one point on a tunable curve. A production
deployment doesn't have to accept the default 0.5 decision threshold --
this shows what recall/FPR looks like at several other operating points,
which is the honest answer to "isn't that FPR too high."

Deliberately NOT applicable to vishing, fake_app_qr, or synthetic_identity
-- those are hybrid Groq+rule/heuristic specialists without a single
probability model over these features, so a threshold sweep wouldn't mean
anything for them. Callers should check applicability before calling this.
"""
import pandas as pd
from sklearn.metrics import confusion_matrix

from app.generate.tabular_generator import generate
from app.defend.feature_utils import FEATURE_COLS

THRESHOLDS = [0.3, 0.5, 0.7, 0.85, 0.95]


def compute_curve(model, attack_id: str, taxonomy_entry: dict | None = None, n: int = 300, seed: int = 777) -> list[dict]:
    legit_df = generate("legit", n=n, seed=seed)
    attack_df = generate(attack_id, n=n, seed=seed + 1, taxonomy_entry=taxonomy_entry)
    df = pd.concat([legit_df, attack_df], ignore_index=True)
    X = df[FEATURE_COLS]
    y = df["label"]

    probs = model.predict_proba(X)[:, 1]
    curve = []
    for t in THRESHOLDS:
        preds = (probs >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, preds, labels=[0, 1]).ravel()
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        curve.append({
            "threshold": t,
            "recall": round(recall, 3),
            "false_positive_rate": round(fpr, 4),
            "precision": round(precision, 3),
        })
    return curve
