"""
Router: decides which specialist handles an incoming case.

DELIBERATELY NO LLM CALL HERE. This runs on every single case, so it needs
to be cheap and fast -- an LLM call per transaction would blow both the
Groq free-tier rate limit and any realistic production latency budget.
Instead: TF-IDF vectorization of each taxonomy entry's description
(fit once, cached) + cosine similarity against a short text summary of the
incoming case, combined with a hard channel-match boost (if the case
declares a channel that matches a taxonomy entry's channel, that's a much
stronger signal than semantic similarity alone).

Below `router_confidence_threshold` -> route to the Generalist instead.
The Generalist ALSO always runs in parallel (cheap, see generalist.py) so
every case gets a second opinion regardless of routing confidence.

GOVERNANCE: only entries with lifecycle_stage == "promoted" are eligible
for live routing (see governance.py). A newly-discovered "shadow" entry
still exists in the taxonomy, still has a trained model, still shows up
in the roster and can be tested directly (Simulate, Arena, evaluation
regimes all call the specialist directly and bypass this router) -- it
just won't be the thing a live, unrouted case gets sent to until it
passes the gate. Seed entries default to "promoted" (they're the 4 deep +
3 originally-seeded auto specialists, trusted from the start).
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.config import settings
from app.taxonomy import taxonomy_store


class Router:
    def __init__(self):
        self._vectorizer: TfidfVectorizer | None = None
        self._taxonomy_matrix = None
        self._taxonomy_ids: list[str] = []
        self._fit()

    def _routable_entries(self) -> list[dict]:
        return [e for e in taxonomy_store.all() if e.get("lifecycle_stage", "promoted") == "promoted"]

    def _fit(self):
        entries = self._routable_entries()
        if not entries:
            # Degenerate case (e.g. right after a reset with nothing
            # promoted yet) -- fit on an empty-but-valid vectorizer rather
            # than crashing.
            self._taxonomy_ids = []
            self._vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
            self._taxonomy_matrix = self._vectorizer.fit_transform(["placeholder"])
            return
        docs = [f"{e['display_name']} {e['description']} {e.get('social_engineering_pattern', '')}"
                for e in entries]
        self._taxonomy_ids = [e["attack_id"] for e in entries]
        self._vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
        self._taxonomy_matrix = self._vectorizer.fit_transform(docs)

    def refit(self):
        """Call after the taxonomy changes (new/promoted entries) so the
        router can route to newly created specialists."""
        self._fit()

    def route(self, case_summary: str, declared_channel: str | None = None) -> dict:
        entries = {e["attack_id"]: e for e in self._routable_entries()}

        if not self._taxonomy_ids:
            return {"attack_id": None, "confidence": 0.0, "use_generalist": True, "scores": {}}

        vec = self._vectorizer.transform([case_summary])
        sims = cosine_similarity(vec, self._taxonomy_matrix)[0]

        scores = {}
        for attack_id, sim in zip(self._taxonomy_ids, sims):
            score = float(sim)
            entry = entries.get(attack_id, {})
            if declared_channel and entry.get("channel") == declared_channel:
                score = min(1.0, score + 0.5)  # hard channel-match boost
            scores[attack_id] = score

        if not scores or max(scores.values()) == 0:
            return {"attack_id": None, "confidence": 0.0, "use_generalist": True, "scores": scores}

        best_id = max(scores, key=scores.get)
        best_score = scores[best_id]
        confident = best_score >= settings.router_confidence_threshold
        return {
            "attack_id": best_id if confident else None,
            "confidence": round(best_score, 4),
            "use_generalist": not confident,
            "scores": {k: round(v, 4) for k, v in sorted(scores.items(), key=lambda x: -x[1])[:3]},
        }


router = Router()
