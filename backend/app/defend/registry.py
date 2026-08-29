"""
Maps a taxonomy entry to its detector.

DEEP tier (specialist_module set to one of the 4 names below) -> the
hand-engineered module for that exact attack type.

Everything else (specialist_tier == "auto", including newly-discovered
entries the closed loop creates) -> auto_specialist, which trains and
serves a real classifier per attack_id -- see auto_specialist.py.
"""
from app.defend.specialists import vishing, fake_app_qr, account_takeover, synthetic_identity
from app.defend.auto_specialist import auto_specialist_store

_DEEP_MODULE_MAP = {
    "vishing": vishing.detect,
    "fake_app_qr": fake_app_qr.detect,
    "account_takeover": account_takeover.detect,
    "synthetic_identity": synthetic_identity.detect,
}


def run_specialist(attack_entry: dict, case: dict) -> dict:
    module_name = attack_entry.get("specialist_module", "")
    fn = _DEEP_MODULE_MAP.get(module_name)
    if fn is not None:
        result = fn(case)
        result.setdefault("signal_breakdown", {})
        result["signal_breakdown"]["tier"] = "deep"
        return result
    return auto_specialist_store.detect(case, attack_entry)
