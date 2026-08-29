"""
For the 4 deep specialists, FEATURE_PROFILES in tabular_generator.py is
hand-curated. For everything else -- the 3 auto-tier seed entries, and any
future entry the closed loop discovers -- there's no hand-curated profile.
This module builds one on demand by asking Groq to reason qualitatively
about the pattern's description ("would this attack show elevated,
normal, or reduced values for each feature?"), then converts that into
the same mean/std/clip format tabular_generator already knows how to
sample from.

Offline fallback: a fixed "generically elevated risk" profile, so the
whole pipeline still works without a Groq key -- less differentiated than
the LLM-reasoned version, but never broken.
"""
from app.groq_client import groq_client
from app.config import settings
from app.defend.feature_utils import FEATURE_COLS, LEGIT_BASELINE

_SYSTEM = (
    "You are a fraud-pattern analyst. For a described payment fraud "
    "pattern, estimate whether each of a fixed set of behavioral features "
    "would be elevated, normal, or reduced relative to legitimate activity."
)

_DIRECTION_MULTIPLIERS = {
    "elevated": 2.2,
    "normal": 1.0,
    "reduced": 0.4,
}

# In-memory cache: built once per attack_id per process lifetime, since the
# taxonomy description doesn't change after creation.
_profile_cache: dict[str, dict] = {}


def _infer_directions(attack_entry: dict) -> dict:
    prompt = (
        f"Attack pattern: {attack_entry.get('display_name')}\n"
        f"Description: {attack_entry.get('description')}\n"
        f"Technical signature: {attack_entry.get('technical_signature')}\n\n"
        f"For each of these features, respond with 'elevated', 'normal', or "
        f"'reduced' relative to a legitimate transaction: {FEATURE_COLS}\n"
        'Return JSON: {"hour_of_day": "...", "device_change": "...", '
        '"geo_velocity_kmh": "...", "tx_velocity_10min": "...", '
        '"login_failed_attempts": "...", "amount_inr": "..."}'
    )
    fallback = {c: "elevated" for c in FEATURE_COLS if c != "hour_of_day"} | {"hour_of_day": "normal"}
    result = groq_client.complete_json(
        prompt, system=_SYSTEM, model=settings.groq_model_fast, offline_fallback=fallback
    )
    return {c: result.get(c, "normal") for c in FEATURE_COLS}


def get_or_build_profile(attack_entry: dict) -> dict:
    attack_id = attack_entry["attack_id"]
    if attack_id in _profile_cache:
        return _profile_cache[attack_id]

    directions = _infer_directions(attack_entry)
    profile = {}
    for feat in FEATURE_COLS:
        base = LEGIT_BASELINE[feat]
        mult = _DIRECTION_MULTIPLIERS.get(directions.get(feat, "normal"), 1.0)
        if feat == "device_change":
            profile[feat] = {"p": min(0.9, base["mean"] * mult + 0.02)}
        else:
            clip_hi = {"hour_of_day": 23, "geo_velocity_kmh": 3000, "tx_velocity_10min": 20,
                       "login_failed_attempts": 10, "amount_inr": 500000}[feat]
            profile[feat] = {
                "mean": base["mean"] * mult if mult != 1.0 else base["mean"],
                "std": base["std"] * max(1.0, mult * 0.8),
                "clip": (0, clip_hi),
            }
    _profile_cache[attack_id] = profile
    return profile
