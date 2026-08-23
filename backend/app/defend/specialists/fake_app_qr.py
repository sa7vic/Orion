"""
Specialist: Fake App / QR Substitution.

Deliberately NOT probabilistic. QR/merchant-identity fraud doesn't need a
classifier -- it needs verification against a source of truth (a merchant
registry / signed app manifest). A deterministic check is faster, cheaper,
has zero false-positive ambiguity, and is more defensible to a regulator
than a model's confidence score would be here.

In production, `verified_merchants.json` would be a live NPCI/bank
merchant registry API; for the hackathon build it's a static JSON fixture
covering a handful of demo merchants (see app/data/verified_merchants.json).
"""
import json
from pathlib import Path
from app.config import settings

_REGISTRY_PATH = Path(settings.data_dir) / "verified_merchants.json"
with open(_REGISTRY_PATH) as f:
    _REGISTRY = json.load(f)


def detect(case: dict) -> dict:
    vpa = case.get("vpa", "")
    qr_hash = case.get("qr_hash")
    app_package = case.get("app_package")
    app_signature = case.get("app_signature")

    reasons = []
    risk = 0.0

    if vpa:
        entry = _REGISTRY["verified_vpas"].get(vpa)
        if entry is None:
            risk += 0.6
            reasons.append(f"VPA '{vpa}' not found in verified merchant registry")
        elif qr_hash and qr_hash != entry["qr_hash"]:
            risk += 0.8
            reasons.append(
                f"QR hash mismatch for registered merchant '{entry['name']}' "
                f"(expected {entry['qr_hash']}, got {qr_hash}) -- possible QR substitution"
            )

    if app_package:
        expected_sig = _REGISTRY["verified_app_signatures"].get(app_package)
        if expected_sig is None:
            risk += 0.5
            reasons.append(f"app package '{app_package}' not in known-good registry")
        elif app_signature and app_signature != expected_sig:
            risk += 0.9
            reasons.append("app signature does not match official package -- likely cloned app")

    risk = min(1.0, risk)
    if not reasons:
        reasons.append("VPA/QR/app signature verified against registry")

    return {
        "specialist": "fake_app_qr_substitution",
        "risk_score": round(risk, 4),
        "reasons": reasons,
        "signal_breakdown": {"check_type": "deterministic_registry_verification"},
    }
