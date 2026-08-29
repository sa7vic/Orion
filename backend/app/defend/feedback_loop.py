"""
The closed loop, made mechanically real -- and now actually trains a
working detector when it fires, not just a name.

Every time a case is processed (see api routes), if:
  - the router couldn't confidently match ANY taxonomy entry (or matched
    only an auto-tier entry whose own model scored it low), AND
  - the generalist independently flags it as anomalous

...it's logged as an "unclaimed anomalous case" against its declared
channel. Once `feedback_promotion_threshold` such cases accumulate for the
same channel, we:
  1. Ask the Identify agent (research_agent.synthesize_new_attack_id) to
     name/describe the pattern from a summary of the cluster.
  2. Write it into the taxonomy store at specialist_tier="auto".
  3. Immediately train a real classifier for it via auto_specialist_store
     -- this is the step that makes the new entry a working detector on
     the spot, not a placeholder waiting for someone to build one later.
  4. Refit the router (new taxonomy entry) so the new entry is routable
     immediately, and retrain the generalist (new feature space).
"""
import threading
from collections import defaultdict

from app.config import settings
from app.taxonomy import taxonomy_store
from app.identify.research_agent import synthesize_new_attack_id

_lock = threading.Lock()
_unclaimed_clusters: dict[str, list[dict]] = defaultdict(list)


def record_case_outcome(case: dict, channel: str, routing: dict, generalist_result: dict, top_specialist_score: float):
    """Call this after every /detect request."""
    unclaimed = routing.get("attack_id") is None or top_specialist_score < 0.4
    if unclaimed and generalist_result.get("is_anomaly"):
        with _lock:
            _unclaimed_clusters[channel].append({
                "summary": case.get("summary", str(case))[:300],
                "generalist_score": generalist_result["risk_score"],
            })
            if len(_unclaimed_clusters[channel]) >= settings.feedback_promotion_threshold:
                cluster = _unclaimed_clusters.pop(channel)
                return _promote(channel, cluster)
    return None


def _promote(channel: str, cluster: list[dict]):
    summary_text = "\n".join(f"- {c['summary']}" for c in cluster)
    new_entry = synthesize_new_attack_id(summary_text, channel)
    new_entry["lifecycle_stage"] = "shadow"  # never starts "promoted" -- must pass the gate first
    taxonomy_store.add_entry(new_entry)

    # Lazy imports to avoid circular import at module load time.
    from app.defend.router import router
    from app.defend.model_store import model_store
    from app.defend.auto_specialist import auto_specialist_store
    from app.defend import governance

    train_metrics = auto_specialist_store.train(new_entry)  # <-- the real step
    router.refit()  # shadow entries are excluded from routing -- see router.py
    model_store.retrain_generalist()

    gate_result = governance.evaluate_gate(new_entry["attack_id"], train_metrics)
    new_entry["lifecycle_stage"] = gate_result["lifecycle_stage"]
    new_entry["gate_result"] = gate_result
    taxonomy_store.add_entry(new_entry)
    if gate_result["passed"]:
        router.refit()  # promoted -- now eligible for live routing, refit to include it

    return {**new_entry, "training_metrics": train_metrics, "gate_result": gate_result}


def get_pending_cluster_sizes() -> dict:
    with _lock:
        return {ch: len(cases) for ch, cases in _unclaimed_clusters.items()}


def _debug_force_promote(channel: str, synthetic_summaries: list[str]):
    """Used by the /simulate/discover-new-pattern demo endpoint to trigger
    a promotion on demand rather than waiting for organic volume."""
    cluster = [{"summary": s, "generalist_score": 0.8} for s in synthetic_summaries]
    return _promote(channel, cluster)
