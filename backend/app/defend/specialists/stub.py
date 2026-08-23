"""
Stub specialist -- backs the 3 taxonomy entries that are intentionally NOT
fully built out (llm_adaptive_chat_scam, agentic_prompt_injection,
b2b_invoice_fraud). Rather than returning nothing, it does one cheap Groq
call for a rough plausibility score, then always defers primary weight to
the Generalist. This is what makes the "watch it get promoted" demo
moment meaningful -- the stub is deliberately weak, so the generalist
catching what the stub misses is a visible, honest gap, not staged.
"""
from app.groq_client import groq_client
from app.config import settings

_SYSTEM = (
    "You give a rough, low-confidence plausibility score for whether a "
    "case matches a described (but not yet deeply modeled) fraud pattern."
)


def detect(case: dict, attack_id: str, description: str) -> dict:
    prompt = (
        f"Fraud pattern (lightly modeled, no dedicated detector yet): {description}\n"
        f"Case summary: {case.get('summary', str(case))}\n\n"
        'Return JSON: {"plausibility_score": <0.0-1.0>, "note": "short reason"}'
    )
    fallback = {"plausibility_score": 0.3, "note": "stub specialist: low-confidence heuristic only"}
    result = groq_client.complete_json(
        prompt, system=_SYSTEM, model=settings.groq_model_fast, offline_fallback=fallback
    )
    score = float(result.get("plausibility_score", 0.3))
    return {
        "specialist": attack_id,
        "risk_score": round(max(0.0, min(1.0, score)), 4),
        "reasons": [result.get("note", "stub specialist -- low confidence"),
                    "no dedicated detector built yet; generalist runs in parallel as primary signal"],
        "signal_breakdown": {"model": "stub", "is_stub": True},
    }
