"""
Specialist: Voice-Clone Vishing.

Two signals combined:
1. Semantic score from Groq: does the transcript contain scam markers
   (urgency, authority impersonation, secrecy request, OTP/PIN request)?
2. Rule-based metadata score: VOIP mask flag, caller reputation, call
   duration outlier.

HARDENING NOTE (read this -- there's a real story here, not just a
weight tweak): the original version weighted semantic 0.65 / metadata
0.35. Live Arena testing (with a real Groq key, not the offline fallback)
found this fully evadable: 0 wins in 9 real adversarial rounds. The red
team's mutation only rewrites the TRANSCRIPT (removing "urgency /
authority / OTP request" language) -- it cannot touch call metadata,
since VOIP-masking and call duration are supposed to be harder to fake.
But because text carried 65% of the weight, a clean rewrite alone was
usually enough to drop the score under the detection threshold, even when
the metadata signal never changed.

Two changes, both defense-in-depth principles a real fraud-ops team would
apply, not metric-gaming:
1. Rebalanced weights (0.45 semantic / 0.55 metadata) so the harder-to-fake
   signal carries more weight than the LLM-rewritable one.
2. A floor: when metadata alone strongly suggests fraud (VOIP-masked +
   short call, or a previously-flagged caller), the final score cannot
   drop below FLOOR_ON_STRONG_METADATA regardless of how clean the
   transcript reads. This is the actual fix -- content alone should never
   fully override a strong behavioral red flag, in a real system or here.

This has NOT been re-validated against a live Groq key by Claude (no API
key in the dev sandbox) -- the offline fallback's semantic score is a flat
constant, so it can't reproduce the exact evasion dynamic that was
observed. Re-run the vishing Arena battle with your own key after pulling
this change and check whether the win rate actually improved; report back
what you see rather than trusting this docstring's intent.
"""
from app.groq_client import groq_client
from app.config import settings

WEIGHTS = {"semantic": 0.45, "metadata": 0.55}

# If metadata_score reaches this, the underlying behavioral signal is
# strong enough that clean-sounding text shouldn't be able to fully clear
# the case -- see hardening note above.
STRONG_METADATA_THRESHOLD = 0.5
FLOOR_ON_STRONG_METADATA = 0.42  # just above the 0.4 "low risk" boundary

_SYSTEM = (
    "You are a fraud-call analyst. Given a call transcript, score how "
    "likely it is a voice-clone/impersonation scam attempting to extract "
    "an OTP or UPI PIN."
)


def _semantic_score(transcript: str) -> tuple[float, list[str]]:
    prompt = (
        f"Transcript:\n{transcript}\n\n"
        'Return JSON: {"scam_score": <0.0-1.0>, "markers": ["urgency", '
        '"authority_impersonation", "otp_request", "secrecy_request", ...]} '
        "Only include markers actually present."
    )
    fallback = {"scam_score": 0.5, "markers": []}
    result = groq_client.complete_json(
        prompt, system=_SYSTEM, model=settings.groq_model_fast, offline_fallback=fallback
    )
    score = float(result.get("scam_score", 0.5))
    markers = result.get("markers", [])
    return max(0.0, min(1.0, score)), markers


def _metadata_score(metadata: dict) -> tuple[float, list[str]]:
    reasons = []
    score = 0.0
    if metadata.get("voip_masked"):
        score += 0.45
        reasons.append("caller ID appears VOIP-masked")
    duration = metadata.get("call_duration_seconds", 120)
    if duration < 90:
        score += 0.25
        reasons.append("unusually short call before sensitive request")
    if metadata.get("caller_reputation", "unknown") == "flagged":
        score += 0.3
        reasons.append("caller number previously flagged")
    return min(1.0, score), reasons


def detect(case: dict) -> dict:
    transcript = case.get("transcript", "")
    metadata = case.get("metadata", {})
    sem_score, sem_markers = _semantic_score(transcript)
    meta_score, meta_reasons = _metadata_score(metadata)
    final = WEIGHTS["semantic"] * sem_score + WEIGHTS["metadata"] * meta_score

    floor_applied = False
    if meta_score >= STRONG_METADATA_THRESHOLD and final < FLOOR_ON_STRONG_METADATA:
        final = FLOOR_ON_STRONG_METADATA
        floor_applied = True

    final = round(final, 4)
    reasons = [f"scam language markers: {', '.join(sem_markers)}"] if sem_markers else []
    reasons += meta_reasons
    if floor_applied:
        reasons.append(
            "strong behavioral signal (VOIP-masking / call pattern) floors the score -- "
            "clean-sounding text alone cannot fully clear this case"
        )

    return {
        "specialist": "vishing_relative_emergency",
        "risk_score": final,
        "reasons": reasons or ["no strong signals detected"],
        "signal_breakdown": {
            "semantic_score": sem_score,
            "metadata_score": meta_score,
            "floor_applied": floor_applied,
        },
    }
