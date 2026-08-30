from datetime import datetime, timezone
from collections import deque

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.taxonomy import taxonomy_store
from app.groq_client import groq_client
from app.generate import tabular_generator, llm_attacker, fidelity
from app.defend.router import router as case_router
from app.defend import feedback_loop, pipeline, adversarial, threshold_analysis, scoreboard, redteam_audit, assurance_report, evaluation_regimes
from app.defend.model_store import model_store
from app.defend.auto_specialist import auto_specialist_store
from app.identify.research_agent import run_research_cycle

app = FastAPI(title="Orion API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pre-train every auto-tier entry at startup so the first real case for it
# doesn't pay the (sub-second, but non-zero) training cost, and so /api/metrics
# has real numbers immediately rather than after a lazy first hit.
auto_specialist_store.ensure_trained_for(taxonomy_store.by_tier("auto"))

# In-memory live feed for the dashboard (most recent N cases). A real
# deployment would use a DB/queue; in-memory keeps the free-tier deploy
# footprint at zero extra infra for the hackathon build.
_LIVE_FEED = deque(maxlen=200)


# ---------- schemas ----------

class SimulateRequest(BaseModel):
    attack_id: str
    n: int = 1


class DetectRequest(BaseModel):
    case: dict
    channel: str | None = None
    summary: str | None = None


class ForcePromoteRequest(BaseModel):
    channel: str
    sample_summaries: list[str]


# ---------- health ----------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "groq_online": groq_client.online,
        "groq_model_fast": settings.groq_model_fast,
        "groq_model_smart": settings.groq_model_smart,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/generate/calibration-status")
def get_calibration_status():
    """Reports whether the Generate pillar's legit/account_takeover
    profiles are Orion's estimates or calibrated against a real dataset --
    see scripts/calibrate_from_real_data.py."""
    return tabular_generator.calibration_status()


# ---------- Identify + taxonomy ----------

@app.get("/api/taxonomy")
def get_taxonomy():
    return {"entries": taxonomy_store.all()}


@app.get("/api/agents")
def get_agents():
    entries = taxonomy_store.all()
    return {
        "specialists": [
            {
                "attack_id": e["attack_id"],
                "display_name": e.get("display_name", e["attack_id"]),
                "tier": e.get("specialist_tier", "auto"),  # "deep" or "auto" -- both fully working
                "channel": e.get("channel", "unknown"),
                "seed_or_discovered": e.get("seed_or_discovered", "seed"),
                "auto_metrics": auto_specialist_store.metrics.get(e["attack_id"]) if e.get("specialist_tier") != "deep" else None,
                "last_researched_at": e.get("last_researched_at"),
                "research_source_count": len(e.get("research_sources", [])),
                "lifecycle_stage": e.get("lifecycle_stage", "promoted"),
                "gate_result": e.get("gate_result"),
            }
            for e in entries
        ],
        "generalist": {"display_name": "Generalist Anomaly Detector", "status": "active", "role": "fallback + novelty sensor"},
    }


@app.post("/api/identify/research/{attack_id}")
def research_pattern(attack_id: str):
    """On-demand research cycle for ONE taxonomy entry -- see
    web_research.py for exactly when/how this runs (short answer:
    only when this endpoint is called, no background scraping)."""
    entry = taxonomy_store.get(attack_id)
    if entry is None:
        raise HTTPException(404, f"unknown attack_id '{attack_id}'")
    updated = run_research_cycle(entry)
    taxonomy_store.add_entry(updated)
    return updated


# ---------- Generate ----------

@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    entry = taxonomy_store.get(req.attack_id)
    if entry is None:
        raise HTTPException(404, f"unknown attack_id '{req.attack_id}'")

    df = tabular_generator.generate(req.attack_id, n=req.n, taxonomy_entry=entry)
    tabular_records = df.to_dict(orient="records")

    unstructured = None
    if req.attack_id == "vishing_relative_emergency":
        unstructured = llm_attacker.generate_vishing_transcript()
    elif req.attack_id == "synthetic_identity_kyc":
        unstructured = llm_attacker.generate_kyc_mismatch_case()
    elif req.attack_id == "llm_adaptive_chat_scam":
        unstructured = llm_attacker.generate_adaptive_chat_snippet()

    return {
        "attack_id": req.attack_id,
        "tabular_records": tabular_records,
        "unstructured_sample": unstructured,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/fidelity/{attack_id}")
def get_fidelity(attack_id: str):
    entry = taxonomy_store.get(attack_id)
    if entry is None:
        raise HTTPException(404, f"unknown attack_id '{attack_id}'")
    # Fidelity compares the synthetic draw for THIS attack type against an
    # independently-seeded second draw of the same type (standing in for a
    # real reference sample of the same class) -- comparing against a
    # different class (e.g. legit) would trivially "fail" by design.
    reference = tabular_generator.generate(attack_id, n=300, seed=101, taxonomy_entry=entry)
    synth = tabular_generator.generate(attack_id, n=300, seed=202, taxonomy_entry=entry)
    score = fidelity.score_fidelity(reference, synth)
    return {"attack_id": attack_id, **score}


# ---------- Defend ----------

@app.post("/api/detect")
def detect(req: DetectRequest):
    verdict = pipeline.run_detection(req.case, req.channel, req.summary)
    case = verdict.pop("_case")

    promoted = feedback_loop.record_case_outcome(
        case, req.channel or "unknown", verdict["routing"], verdict["generalist_result"],
        verdict["specialist_result"]["risk_score"] if verdict["specialist_result"] else 0.0,
    )
    if promoted:
        verdict["triggered_promotion"] = promoted

    _LIVE_FEED.appendleft(verdict)
    return verdict


@app.post("/api/adversarial/evolve/{attack_id}")
def evolve_attack(attack_id: str):
    """Red team explicitly attacks the blue team's own detector: generate
    an attack, detect it, mutate it to try to evade what caught it,
    detect the mutation. See adversarial.py for the full explanation."""
    result = adversarial.evolve(attack_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.post("/api/arena/battle/{attack_id}")
def battle(attack_id: str, rounds: int = 5):
    """Run a multi-round red-vs-blue match for one attack type. Each
    round is scored independently and feeds the persistent scoreboard --
    see scoreboard.py."""
    if rounds < 1 or rounds > 10:
        raise HTTPException(400, "rounds must be between 1 and 10")
    result = adversarial.run_battle(attack_id, rounds=rounds)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.get("/api/arena/scoreboard")
def get_scoreboard():
    return scoreboard.summary()


@app.post("/api/arena/scoreboard/reset")
def reset_scoreboard():
    scoreboard.reset()
    return {"status": "reset"}


@app.post("/api/audit/run")
def run_redteam_audit(rounds_per_attack: int = 3):
    """Run a periodic red-teaming audit across every eligible specialist.
    This operationalizes RBI's FREE-AI Committee Report (Protection pillar,
    Recommendation 20) recommendation for 'structured red teaming across the
    AI lifecycle' -- see redteam_audit.py for the exact citation and what this
    deliberately does NOT do (no invented grade or pass/fail threshold)."""
    if rounds_per_attack < 1 or rounds_per_attack > 5:
        raise HTTPException(400, "rounds_per_attack must be between 1 and 5")
    return redteam_audit.run_audit(rounds_per_attack=rounds_per_attack)


@app.get("/api/audit/history")
def get_audit_history():
    return {"history": redteam_audit.get_history_summary()}


@app.get("/api/audit/latest")
def get_latest_audit():
    latest = redteam_audit.get_latest()
    if latest is None:
        raise HTTPException(404, "no audit has been run yet")
    return latest


@app.get("/api/audit/{audit_id}")
def get_audit_by_id(audit_id: str):
    report = redteam_audit.get_by_id(audit_id)
    if report is None:
        raise HTTPException(404, f"no audit found with id '{audit_id}'")
    return report


@app.post("/api/audit/full-report")
def generate_full_assurance_report(rounds_per_attack: int = 3):
    """The exportable artifact -- audit + fidelity + FPR + discovered
    patterns + model versions + the required disclaimer, in one document.
    See assurance_report.py."""
    if rounds_per_attack < 1 or rounds_per_attack > 5:
        raise HTTPException(400, "rounds_per_attack must be between 1 and 5")
    return assurance_report.generate_report(rounds_per_attack=rounds_per_attack)


@app.get("/api/feed")
def get_feed(limit: int = 30):
    return {"cases": list(_LIVE_FEED)[:limit]}


@app.get("/api/feedback/pending")
def get_pending_clusters():
    return {"pending": feedback_loop.get_pending_cluster_sizes(),
            "promotion_threshold": settings.feedback_promotion_threshold}


@app.post("/api/feedback/force-promote")
def force_promote(req: ForcePromoteRequest):
    """Demo-only endpoint: manually trigger a promotion without waiting for
    organic case volume, so the closed loop can be shown live in a short demo."""
    new_entry = feedback_loop._debug_force_promote(req.channel, req.sample_summaries)
    return {"promoted": new_entry}


# ---------- Metrics ----------

@app.get("/api/metrics/threshold-curve/{attack_id}")
def get_threshold_curve(attack_id: str):
    """Recall/FPR tradeoff at several decision thresholds -- turns a
    single reported FPR into a tunable curve. Only meaningful for models
    with a single probability output over the standard feature set
    (account_takeover's GBM, and every auto-tier LogisticRegression) --
    the other 3 deep specialists are hybrid Groq+rule systems this
    doesn't apply to."""
    entry = taxonomy_store.get(attack_id)
    if entry is None:
        raise HTTPException(404, f"unknown attack_id '{attack_id}'")

    if attack_id == "account_takeover":
        model = model_store.ato_model
    elif attack_id in auto_specialist_store._models or entry.get("specialist_tier") == "auto":
        if not auto_specialist_store.is_trained(attack_id):
            auto_specialist_store.train(entry)
        model = auto_specialist_store._models[attack_id]
    else:
        raise HTTPException(
            400,
            f"'{attack_id}' is a hybrid Groq/rule-based specialist without a single "
            "probability model over the standard features -- a threshold sweep isn't "
            "meaningful for it (see vishing.py / fake_app_qr.py / synthetic_identity.py).",
        )

    curve = threshold_analysis.compute_curve(model, attack_id, taxonomy_entry=entry)
    return {"attack_id": attack_id, "default_threshold": 0.5, "curve": curve}


@app.get("/api/metrics/evaluation-regimes/{attack_id}")
def get_evaluation_regimes(attack_id: str):
    """IID vs cross-generator vs adversarial-OOD -- three evaluation
    regimes instead of one headline number. See evaluation_regimes.py."""
    entry = taxonomy_store.get(attack_id)
    if entry is None:
        raise HTTPException(404, f"unknown attack_id '{attack_id}'")

    if attack_id == "account_takeover":
        model = model_store.ato_model
    elif entry.get("specialist_tier") == "auto":
        if not auto_specialist_store.is_trained(attack_id):
            auto_specialist_store.train(entry)
        model = auto_specialist_store._models[attack_id]
    else:
        raise HTTPException(
            400,
            f"'{attack_id}' is a hybrid Groq/rule-based specialist without a single "
            "probability model -- evaluation regimes aren't meaningful for it.",
        )

    return evaluation_regimes.evaluate_regimes(attack_id, entry, model)


@app.get("/api/metrics")
def get_metrics():
    deep_metrics = dict(model_store.last_training_metrics)
    generalist_metrics = deep_metrics.pop("generalist", None)
    return {
        "deep_tier_metrics": deep_metrics,
        "auto_tier_metrics": auto_specialist_store.metrics,
        "generalist_metrics": generalist_metrics,
        "note": "Computed on held-out synthetic data generated by the Generate pillar "
                "(see /api/fidelity for how closely that data tracks real distributions). "
                "Auto-tier metrics come from a lightweight LogisticRegression trained on an "
                "LLM-inferred feature profile at entry-creation time -- see auto_specialist.py. "
                "IMPORTANT: both train and test data come from the same synthetic generator, "
                "so these numbers show the model learned its own generator's distribution, not "
                "necessarily real-world generalization -- see /api/adversarial/evolve for a "
                "genuine out-of-distribution stress test.",
    }


# ---------- Reset (demo convenience) ----------

@app.post("/api/reset")
def reset_demo():
    taxonomy_store.reset()
    case_router.refit()
    _LIVE_FEED.clear()
    groq_client.clear_cache()
    auto_specialist_store._models.clear()
    auto_specialist_store.metrics.clear()
    from app.generate.profile_inference import _profile_cache
    _profile_cache.clear()
    auto_specialist_store.ensure_trained_for(taxonomy_store.by_tier("auto"))
    scoreboard.reset()
    redteam_audit.reset()
    return {"status": "reset"}
