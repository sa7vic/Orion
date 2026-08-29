"""
Generate pillar -- structured/tabular side.

DESIGN NOTE (read this before assuming SDV/CTGAN was forgotten):
SDV's neural synthesizers (CTGAN/TVAE) pull in PyTorch, which is a 2-4GB
dependency and needs real training time per attack type. For a hackathon
judged on a live demo running on free-tier compute, that's a liability, not
a feature. Instead we implement a Gaussian-copula-style generator by hand:

  1. Fit marginal distributions per feature per class (legit vs each attack
     type) from a small set of realistic seed statistics (calibrated against
     publicly documented fraud patterns -- see FEATURE_PROFILES below).
  2. Sample correlated features via a multivariate normal copula, then
     inverse-transform through each marginal.

This is the same statistical idea SDV's GaussianCopulaSynthesizer uses,
implemented in ~100 lines of numpy with zero heavy dependencies -- it
trains instantly and runs identically on a free Render/HF Spaces instance.
`fidelity.py` scores its output the same way regardless of which generator
produced it, so swapping in real SDV/CTGAN later (e.g. once you've pulled
the real IEEE-CIS / PaySim datasets from Kaggle) is a drop-in replacement:
implement the same `generate(attack_id, n)` interface.

REAL-DATA CALIBRATION: if `app/data/calibrated_profiles.json` exists (see
scripts/calibrate_from_real_data.py), the "legit" and "account_takeover"
profiles below are overridden feature-by-feature with statistics computed
from a real dataset, for every feature that dataset actually covers.
Features the real dataset doesn't cover fall back to the estimates below.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

_CALIBRATED_PATH = Path(__file__).parent.parent / "data" / "calibrated_profiles.json"


def _load_calibration() -> dict | None:
    if not _CALIBRATED_PATH.exists():
        return None
    try:
        with open(_CALIBRATED_PATH) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 -- a malformed calibration file should
        # never crash startup; fall back to estimated profiles instead.
        return None


_calibration = _load_calibration()


def calibration_status() -> dict:
    """Exposed via /api/generate/calibration-status so the UI can honestly
    show whether profiles are estimated or calibrated against real data."""
    if _calibration is None:
        return {
            "calibrated": False,
            "message": "Using estimated profiles. Run scripts/calibrate_from_real_data.py "
                       "against a real dataset (e.g. PaySim from Kaggle) to calibrate.",
        }
    meta = _calibration.get("_metadata", {})
    return {"calibrated": True, **meta}


def _apply_calibration(profiles: dict) -> dict:
    if _calibration is None:
        return profiles
    merged = {k: dict(v) for k, v in profiles.items()}
    for attack_id in ("legit", "account_takeover"):
        cal_entry = _calibration.get(attack_id)
        if not cal_entry:
            continue
        for feat, spec in cal_entry.items():
            # Only override features that were ACTUALLY calibrated (have a
            # mean/std) -- "not available" stub entries are skipped, so
            # Orion's estimate is used for anything the real dataset
            # doesn't cover, rather than silently zeroing it out.
            if "mean" in spec and "std" in spec:
                merged[attack_id][feat] = {
                    "mean": spec["mean"],
                    "std": spec["std"],
                    "clip": tuple(spec["clip"]),
                }
    return merged

# Per-attack-type feature profiles: mean/std for a multivariate-normal
# latent space, plus the marginal transform applied to each dimension.
#
# RESEARCH GROUNDING (full citations in RESEARCH.md):
#
# Grounded with real published numbers:
# - legit.amount_inr: NPCI FY2025-26 data puts the average UPI ticket size
#   at ~Rs 1,300-1,400 (Rs 314 lakh crore / 24,162 crore transactions),
#   with 86% of P2M transactions in the Rs 0-500 band. [NPCI/PIB, 2026]
# - fake_app_qr_substitution.amount_inr: 2026 fraud reporting explicitly
#   flags micro-transactions under Rs 500 as a tactic to stay under alert
#   thresholds -- this profile's low mean reflects that directly.
# - account_takeover / vishing amount_inr: reporting citing RBI data puts
#   average merchant loss before detection at Rs 50,000-5,00,000 per
#   incident, informing the order of magnitude used here.
#
# Directionally grounded, magnitude estimated (real signal, no public
# numeric threshold exists -- fraud vendors don't publish these):
# device_change, geo_velocity_kmh, tx_velocity_10min, login_failed_attempts
# as ATO signals are industry-standard velocity-check / geo-velocity
# practice [Stripe, FraudNet, Veriff]. That these features MATTER is
# well-documented; the specific mean/std assigned per attack type below is
# still an informed estimate.
#
# LIMITATION THAT MATTERS: real fraud is rare (PaySim: 0.13% of
# transactions; a widely-used credit-card fraud benchmark: 0.17%). This
# synthetic dataset is deliberately balanced (~50/50 legit/attack) for
# trainability -- reported precision/recall/F1 describe performance on
# that balanced set, NOT expected real-world performance at a ~0.1-0.5%
# base rate, where false-positive volume dominates. A production system
# needs explicit class-imbalance handling; flagged here, not hidden.
FEATURE_PROFILES = {
    "legit": {
        "hour_of_day": {"mean": 14, "std": 4, "clip": (0, 23)},
        "device_change": {"p": 0.03},
        "geo_velocity_kmh": {"mean": 5, "std": 8, "clip": (0, 900)},
        "tx_velocity_10min": {"mean": 1, "std": 0.8, "clip": (0, 20)},
        "login_failed_attempts": {"mean": 0.1, "std": 0.3, "clip": (0, 10)},
        # Grounded: NPCI FY2025-26 average UPI ticket size ~Rs 1,300-1,400.
        "amount_inr": {"mean": 1350, "std": 1900, "clip": (10, 500000)},
    },
    "account_takeover": {
        "hour_of_day": {"mean": 3, "std": 3, "clip": (0, 23)},
        "device_change": {"p": 0.85},
        "geo_velocity_kmh": {"mean": 650, "std": 300, "clip": (0, 3000)},
        "tx_velocity_10min": {"mean": 6, "std": 3, "clip": (0, 20)},
        "login_failed_attempts": {"mean": 3.5, "std": 2, "clip": (0, 10)},
        # Grounded: reporting citing RBI puts avg merchant fraud loss
        # before detection at Rs 50,000-5,00,000; midpoint-anchored here.
        "amount_inr": {"mean": 60000, "std": 35000, "clip": (10, 500000)},
    },
    "vishing_relative_emergency": {
        "hour_of_day": {"mean": 12, "std": 5, "clip": (0, 23)},
        "device_change": {"p": 0.15},
        "geo_velocity_kmh": {"mean": 10, "std": 15, "clip": (0, 900)},
        "tx_velocity_10min": {"mean": 1.2, "std": 0.6, "clip": (0, 20)},
        "login_failed_attempts": {"mean": 0.2, "std": 0.5, "clip": (0, 10)},
        # Grounded: same Rs 50,000-5,00,000 loss-before-detection range,
        # lower end since vishing typically extracts one OTP/PIN per call
        # rather than a merchant's full exposure.
        "amount_inr": {"mean": 32000, "std": 20000, "clip": (10, 500000)},
    },
    "fake_app_qr_substitution": {
        "hour_of_day": {"mean": 15, "std": 5, "clip": (0, 23)},
        "device_change": {"p": 0.05},
        "geo_velocity_kmh": {"mean": 4, "std": 6, "clip": (0, 900)},
        "tx_velocity_10min": {"mean": 1, "std": 0.5, "clip": (0, 20)},
        "login_failed_attempts": {"mean": 0.1, "std": 0.3, "clip": (0, 10)},
        # Grounded: 2026 fraud reporting flags sub-Rs-500 micro-transactions
        # as an explicit tactic to stay under bank alert thresholds.
        "amount_inr": {"mean": 380, "std": 260, "clip": (10, 2000)},
    },
    "synthetic_identity_kyc": {
        "hour_of_day": {"mean": 13, "std": 6, "clip": (0, 23)},
        "device_change": {"p": 0.4},
        "geo_velocity_kmh": {"mean": 20, "std": 40, "clip": (0, 900)},
        "tx_velocity_10min": {"mean": 0.5, "std": 0.4, "clip": (0, 20)},
        "login_failed_attempts": {"mean": 0.3, "std": 0.6, "clip": (0, 10)},
        "amount_inr": {"mean": 100, "std": 50, "clip": (10, 500000)},
    },
}

# Applied here, not at definition time -- overrides "legit" and
# "account_takeover" feature-by-feature with real calibrated statistics if
# scripts/calibrate_from_real_data.py has been run. No-op otherwise.
FEATURE_PROFILES = _apply_calibration(FEATURE_PROFILES)

# Correlation structure shared across profiles (kept simple/symmetric):
# device_change, geo_velocity and login_failed_attempts tend to move
# together in real account-takeover fraud; hour_of_day is semi-independent.
_FEATURES = ["hour_of_day", "device_change", "geo_velocity_kmh", "tx_velocity_10min",
             "login_failed_attempts", "amount_inr"]
_CORR = np.array([
    [1.0, 0.05, 0.05, 0.05, 0.05, 0.0],
    [0.05, 1.0, 0.55, 0.35, 0.5, 0.15],
    [0.05, 0.55, 1.0, 0.4, 0.45, 0.1],
    [0.05, 0.35, 0.4, 1.0, 0.3, 0.2],
    [0.05, 0.5, 0.45, 0.3, 1.0, 0.1],
    [0.0, 0.15, 0.1, 0.2, 0.1, 1.0],
])


def _sample_latent(n: int, seed: int | None = None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.multivariate_normal(mean=np.zeros(len(_FEATURES)), cov=_CORR, size=n)


def _to_uniform(latent_col: np.ndarray) -> np.ndarray:
    from scipy.stats import norm
    return norm.cdf(latent_col)


def generate(attack_id: str, n: int = 50, seed: int | None = None, taxonomy_entry: dict | None = None) -> pd.DataFrame:
    """Generate n synthetic session/transaction rows for a given attack_id
    (or 'legit' for legitimate traffic used as the negative class).

    If attack_id isn't in the hand-curated FEATURE_PROFILES (true for
    auto-tier and newly-discovered entries), pass `taxonomy_entry` so a
    profile can be inferred on the fly -- see profile_inference.py."""
    if attack_id in FEATURE_PROFILES:
        profile = FEATURE_PROFILES[attack_id]
    elif taxonomy_entry is not None:
        from app.generate.profile_inference import get_or_build_profile
        profile = get_or_build_profile(taxonomy_entry)
    else:
        profile = FEATURE_PROFILES["account_takeover"]
    latent = _sample_latent(n, seed)
    cols = {}
    for i, feat in enumerate(_FEATURES):
        u = _to_uniform(latent[:, i])
        spec = profile[feat]
        if feat == "device_change":
            cols[feat] = (u < spec["p"]).astype(int)
        else:
            from scipy.stats import norm
            vals = norm.ppf(u, loc=spec["mean"], scale=spec["std"])
            lo, hi = spec["clip"]
            cols[feat] = np.clip(vals, lo, hi)
    df = pd.DataFrame(cols)
    df["hour_of_day"] = df["hour_of_day"].round().astype(int).clip(0, 23)
    df["tx_velocity_10min"] = df["tx_velocity_10min"].round().astype(int).clip(0, 20)
    df["login_failed_attempts"] = df["login_failed_attempts"].round().astype(int).clip(0, 10)
    df["amount_inr"] = df["amount_inr"].round(2)
    df["attack_id"] = attack_id
    df["label"] = 0 if attack_id == "legit" else 1
    return df


def generate_mixed_dataset(n_legit: int = 400, n_per_attack: int = 100, seed: int = 42) -> pd.DataFrame:
    """Balanced-ish dataset used to bootstrap-train the account-takeover
    specialist and the generalist anomaly detector at startup."""
    frames = [generate("legit", n_legit, seed)]
    for attack_id in FEATURE_PROFILES:
        if attack_id == "legit":
            continue
        frames.append(generate(attack_id, n_per_attack, seed + hash(attack_id) % 1000))
    return pd.concat(frames, ignore_index=True)
