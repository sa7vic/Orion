"""
Specialist: Synthetic Identity / Deepfake KYC.

Two signals:
1. Field-consistency check: does the application form match the submitted
   document (name/DOB/address)? Scored via Groq for fuzzy/semantic
   matching (handles spelling variants, transliteration, etc. better than
   exact string match).
2. Image artifact heuristic: a lightweight frequency-domain noise-pattern
   check on the submitted photo as a stand-in for a real deepfake
   detector. See note below -- this is intentionally NOT presented as a
   production-grade deepfake detector.

HONEST SCOPE NOTE: real deepfake-artifact detection needs a pretrained
model (e.g. a frequency-domain CNN) with real GPU-trained weights, which
isn't obtainable inside a free-tier, no-GPU hackathon build. The heuristic
here (`_image_artifact_heuristic`) computes a simple high-frequency noise
consistency score from the image -- real synthetic-face generators often
leave subtly different noise statistics than camera sensors. It's a
legitimate, cheap, explainable signal, but it should be labeled to judges
as a heuristic proxy, with the upgrade path (swap in a HuggingFace
deepfake-detection checkpoint) noted in the README.
"""
import numpy as np
from PIL import Image
import io

from app.groq_client import groq_client
from app.config import settings

_SYSTEM = (
    "You compare two sets of identity fields (application form vs "
    "submitted document) and flag inconsistencies indicative of synthetic "
    "identity fraud. Consider spelling variants and transliteration as "
    "consistent, not inconsistent."
)


def _field_consistency_score(application_fields: dict, document_fields: dict) -> tuple[float, list[str]]:
    prompt = (
        f"Application form fields: {application_fields}\n"
        f"Document fields: {document_fields}\n\n"
        'Return JSON: {"inconsistency_score": <0.0-1.0>, "flagged_fields": ["..."]}'
    )
    fallback = {"inconsistency_score": 0.5, "flagged_fields": []}
    result = groq_client.complete_json(
        prompt, system=_SYSTEM, model=settings.groq_model_fast, offline_fallback=fallback
    )
    score = float(result.get("inconsistency_score", 0.5))
    return max(0.0, min(1.0, score)), result.get("flagged_fields", [])


def _image_artifact_heuristic(image_bytes: bytes | None) -> tuple[float, str]:
    """Cheap high-frequency noise consistency heuristic -- proxy signal,
    not a production deepfake detector. See module docstring."""
    if not image_bytes:
        return 0.0, "no image supplied"
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        arr = np.asarray(img, dtype=np.float32)
        # Laplacian-based high-frequency energy as a rough noise-pattern proxy.
        lap = np.abs(np.diff(arr, axis=0)[:, :-1]) + np.abs(np.diff(arr, axis=1)[:-1, :])
        noise_energy = float(lap.std())
        # Real camera sensor noise tends to sit in a mid range; unusually
        # smooth (low) or unusually uniform-high energy are both flagged
        # as heuristic anomalies -- deliberately loose thresholds.
        if noise_energy < 3.0 or noise_energy > 60.0:
            return 0.55, f"atypical noise-energy signature ({noise_energy:.1f})"
        return 0.1, f"noise-energy signature within typical range ({noise_energy:.1f})"
    except Exception:
        return 0.0, "image could not be analyzed"


def detect(case: dict) -> dict:
    app_fields = case.get("application_fields", {})
    doc_fields = case.get("document_fields", {})
    image_bytes = case.get("image_bytes")

    field_score, flagged = _field_consistency_score(app_fields, doc_fields)
    image_score, image_note = _image_artifact_heuristic(image_bytes)

    final = round(0.7 * field_score + 0.3 * image_score, 4)
    reasons = []
    if flagged:
        reasons.append(f"field inconsistency in: {', '.join(flagged)}")
    reasons.append(image_note)

    return {
        "specialist": "synthetic_identity_kyc",
        "risk_score": final,
        "reasons": reasons,
        "signal_breakdown": {
            "field_consistency_score": field_score,
            "image_heuristic_score": image_score,
            "image_check_type": "heuristic_proxy_not_production_deepfake_detector",
        },
    }
