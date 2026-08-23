"""
Fidelity scoring for the Generate pillar -- turns "does this look realistic"
into a number, per the challenge's explicit fidelity criterion.

Two checks, both cheap and dependency-light:
1. Discriminator score: train a simple classifier to distinguish real vs
   synthetic rows. If it can't do much better than chance (AUC ~0.5), the
   synthetic data is statistically hard to tell apart from real -- good.
   AUC close to 1.0 means the synthetic data is easily distinguishable --
   needs work.
2. KS-test per feature: two-sample Kolmogorov-Smirnov test comparing each
   feature's distribution between real and synthetic. Reports which
   features (if any) diverge significantly.

"Real" reference distribution: for the hackathon build this is a second,
independently-seeded draw from the same generator's legit profile scaled
to mimic aggregate statistics documented in public fraud reports (IEEE-CIS/
PaySim-style order of magnitude for amount/velocity). Swap in the actual
downloaded IEEE-CIS/PaySim CSVs for the real production fidelity check --
this module's interface (`score_fidelity(real_df, synth_df)`) doesn't
change either way.
"""
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

NUMERIC_FEATURES = ["hour_of_day", "geo_velocity_kmh", "tx_velocity_10min",
                     "login_failed_attempts", "amount_inr"]


def score_fidelity(real_df: pd.DataFrame, synth_df: pd.DataFrame) -> dict:
    real = real_df.copy()
    synth = synth_df.copy()
    real["is_synthetic"] = 0
    synth["is_synthetic"] = 1
    combined = pd.concat([real, synth], ignore_index=True)

    X = combined[NUMERIC_FEATURES + ["device_change"]]
    y = combined["is_synthetic"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    clf = GradientBoostingClassifier(n_estimators=60, max_depth=2, random_state=42)
    clf.fit(X_train, y_train)
    probs = clf.predict_proba(X_test)[:, 1]
    discriminator_auc = float(roc_auc_score(y_test, probs))
    # Distance from 0.5 = how easily real/synthetic are told apart.
    # 0 = indistinguishable (best), 0.5 = perfectly distinguishable (worst).
    fidelity_score = round(1 - 2 * abs(discriminator_auc - 0.5), 4)

    ks_results = {}
    for feat in NUMERIC_FEATURES:
        stat, p = ks_2samp(real_df[feat], synth_df[feat])
        ks_results[feat] = {"ks_stat": round(float(stat), 4), "p_value": round(float(p), 4)}

    return {
        "discriminator_auc": round(discriminator_auc, 4),
        "fidelity_score": fidelity_score,
        "interpretation": (
            "High distributional fidelity (indistinguishable from a held-out reference draw "
            "of the same calibrated distribution -- NOT a claim of matching real-world data "
            "unless that reference is itself real, see calibration-status)"
            if fidelity_score > 0.7
            else "Moderate distributional fidelity" if fidelity_score > 0.4
            else "Low distributional fidelity (easily distinguishable from the reference) -- tune FEATURE_PROFILES"
        ),
        "ks_per_feature": ks_results,
    }
