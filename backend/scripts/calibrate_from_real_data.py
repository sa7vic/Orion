"""
Calibrate Orion's synthetic legit/account-takeover profiles against a real
public fraud dataset (PaySim), instead of the estimated statistics Orion
ships with by default.

WHY THIS IS A SEPARATE SCRIPT, NOT BUILT INTO THE APP: Kaggle requires
authentication and isn't reachable from Claude's sandboxed dev environment
(network allowlisted to package registries only). Run this on your own
machine, which has normal internet access.

USAGE
  1. Download PaySim from Kaggle (free account required):
     https://www.kaggle.com/datasets/ntnu-testimon/paysim1
     (~470MB CSV, named like PS_20174392719_1491204439457_log.csv)
  2. python scripts/calibrate_from_real_data.py --csv /path/to/paysim.csv
  3. Restart the backend. tabular_generator.py automatically loads
     app/data/calibrated_profiles.json if present, and /api/health-style
     endpoints will report calibration status once this file exists.

WHAT THIS DOES AND DOES NOT CALIBRATE -- read before citing "real data" --
PaySim's schema only supports calibrating 3 of Orion's 6 features:
  - hour_of_day: from `step` (1 step = 1 simulated hour), step % 24
  - amount_inr: from `amount` directly (see currency note below)
  - tx_velocity_10min: approximated via per-account transaction counts
    within the same step (PaySim has no sub-hour timestamps, so this is
    coarser than a real 10-minute window -- an approximation, not exact)
PaySim has NO device, geolocation, or login-attempt data.
device_change, geo_velocity_kmh, and login_failed_attempts are NOT
calibrated by this script -- they remain Orion's estimated values, and
this script does not silently invent numbers for them. tabular_generator.py
falls back to the built-in estimate for anything the calibration file
doesn't cover.

NOTE ON CURRENCY: PaySim's `amount` field is a synthetic mobile-money
value from a simulator calibrated against real African mobile-money
transaction logs -- it is NOT literally in INR. This script uses it for
the relative SHAPE of the legit-vs-fraud amount distribution (ratios,
skew, spread), not as an authoritative absolute Rupee figure. Say this
plainly if citing calibrated numbers -- PaySim does not give an
India-specific Rupee distribution.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

OUTPUT_PATH = Path(__file__).parent.parent / "app" / "data" / "calibrated_profiles.json"


def load_paysim(csv_path: str) -> pd.DataFrame:
    print(f"Loading {csv_path} ...")
    df = pd.read_csv(csv_path)
    required = {"step", "amount", "isFraud"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected PaySim columns: {missing}. Is this really a PaySim export?")
    return df


def compute_velocity_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """Rough tx-count-per-step-per-account proxy for tx_velocity_10min.
    PaySim has no sub-hour timestamps, so this is coarser than the name
    implies -- documented as an approximation, not exact."""
    if "nameOrig" not in df.columns:
        df["tx_velocity_proxy"] = 1
        return df
    counts = df.groupby(["nameOrig", "step"]).size().rename("tx_velocity_proxy")
    return df.merge(counts, on=["nameOrig", "step"], how="left")


def build_profile(df: pd.DataFrame, label: int) -> dict:
    subset = df[df["isFraud"] == label]
    if len(subset) == 0:
        raise ValueError(f"No rows with isFraud={label} found -- check the CSV.")

    hours = subset["step"] % 24
    amounts = subset["amount"]
    velocity = subset["tx_velocity_proxy"]

    return {
        "hour_of_day": {
            "mean": round(float(hours.mean()), 2),
            "std": round(float(hours.std()), 2),
            "clip": [0, 23],
            "source": "real (PaySim step % 24)",
        },
        "amount_inr": {
            "mean": round(float(amounts.mean()), 2),
            "std": round(float(amounts.std()), 2),
            "clip": [10, round(float(amounts.quantile(0.999)), 2)],
            "source": "real (PaySim amount -- NOT literal INR, distribution shape only, see script docstring)",
        },
        "tx_velocity_10min": {
            "mean": round(float(velocity.mean()), 2),
            "std": round(float(velocity.std()), 2),
            "clip": [0, 20],
            "source": "approximated (PaySim has no sub-hour timestamps; per-step transaction count used as proxy)",
        },
        "device_change": {"source": "not available in PaySim -- Orion's estimated value is used instead"},
        "geo_velocity_kmh": {"source": "not available in PaySim -- Orion's estimated value is used instead"},
        "login_failed_attempts": {"source": "not available in PaySim -- Orion's estimated value is used instead"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", required=True, help="Path to the PaySim CSV")
    args = parser.parse_args()

    df = load_paysim(args.csv)
    df = compute_velocity_proxy(df)

    fraud_rate = df["isFraud"].mean()
    print(f"Loaded {len(df):,} rows -- {int(df['isFraud'].sum()):,} fraud, "
          f"{int((df['isFraud'] == 0).sum()):,} legit ({100 * fraud_rate:.3f}% fraud rate)")

    calibrated = {
        "legit": build_profile(df, label=0),
        "account_takeover": build_profile(df, label=1),
        "_metadata": {
            "source_dataset": "PaySim (Kaggle: ntnu-testimon/paysim1)",
            "rows_used": len(df),
            "real_fraud_rate": round(float(fraud_rate), 5),
            "calibrated_features": ["hour_of_day", "amount_inr", "tx_velocity_10min"],
            "not_calibrated_features": ["device_change", "geo_velocity_kmh", "login_failed_attempts"],
            "currency_note": "PaySim's amount field is a synthetic mobile-money value, not literal INR -- "
                              "used for real-vs-fraud distribution SHAPE, not an authoritative Rupee figure.",
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(calibrated, f, indent=2)

    print(f"\nWrote calibrated profiles to {OUTPUT_PATH}")
    print("Restart the backend -- tabular_generator.py will load this automatically.")
    print(f"\nReal fraud rate in this dataset: {100 * fraud_rate:.3f}% "
          "(compare against Orion's balanced ~50/50 training set -- a real class-imbalance gap, "
          "see tabular_generator.py's limitation note).")


if __name__ == "__main__":
    main()
