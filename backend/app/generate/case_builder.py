"""
Turns a Generate-pillar output (one tabular record + optional unstructured
sample) into the case shape each specialist expects. This mirrors
frontend/src/pages/Simulate.jsx's buildCasePayload() -- kept as a
deliberate parallel implementation (not a shared library) since frontend
JS and backend Python can't share code directly here, but the two must
stay in sync. If you change one, change the other.
"""


def build_case(attack_id: str, record: dict, unstructured: dict | None) -> dict:
    if attack_id == "vishing_relative_emergency":
        return {
            "transcript": (unstructured or {}).get("transcript", "No transcript generated."),
            "metadata": {
                "voip_masked": record.get("device_change") == 1,
                "call_duration_seconds": max(20, 200 - record.get("tx_velocity_10min", 1) * 25),
                "caller_reputation": "flagged" if record.get("login_failed_attempts", 0) > 1 else "unknown",
            },
        }
    if attack_id == "fake_app_qr_substitution":
        return {
            "vpa": "chaicorner@okicici",
            "qr_hash": "ffff0000",  # fraudulent by construction, for demo/eval purposes
            "metadata": {
                "hour_of_day": record.get("hour_of_day"),
                "device_change": record.get("device_change"),
                "geo_velocity_kmh": record.get("geo_velocity_kmh"),
                "tx_velocity_10min": record.get("tx_velocity_10min"),
                "login_failed_attempts": record.get("login_failed_attempts"),
                "amount_inr": record.get("amount_inr"),
            },
        }
    if attack_id == "account_takeover":
        return {
            "session_features": {
                "hour_of_day": record.get("hour_of_day"),
                "device_change": record.get("device_change"),
                "geo_velocity_kmh": record.get("geo_velocity_kmh"),
                "tx_velocity_10min": record.get("tx_velocity_10min"),
                "login_failed_attempts": record.get("login_failed_attempts"),
                "amount_inr": record.get("amount_inr"),
            }
        }
    if attack_id == "synthetic_identity_kyc":
        return {
            "application_fields": (unstructured or {}).get("application_fields", {"name": "Unknown"}),
            "document_fields": (unstructured or {}).get("document_fields", {"name": "Unknown"}),
        }
    return {
        "summary": (unstructured or {}).get("chat", f"Simulated {attack_id} case"),
        "metadata": {
            "hour_of_day": record.get("hour_of_day"),
            "device_change": record.get("device_change"),
            "geo_velocity_kmh": record.get("geo_velocity_kmh"),
            "tx_velocity_10min": record.get("tx_velocity_10min"),
            "login_failed_attempts": record.get("login_failed_attempts"),
            "amount_inr": record.get("amount_inr"),
        },
    }
