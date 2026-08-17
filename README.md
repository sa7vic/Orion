# Orion

A closed-loop red-team/blue-team system: **Identify** emerging GenAI payment fraud patterns → **Generate** realistic synthetic attacks at scale → **Defend** with a mixture of specialist detectors + a generalist safety net that feeds discoveries back into Identify. Fully working, runs on free-tier infrastructure, one API dependency (Groq).

---

## Architecture recap

```
Identify (1 research agent)  →  Taxonomy Store (shared schema)
        ↑                              ↓
        |                    Generate (tabular + LLM-scripted content)
        |                              ↓
        |                    Defend: Router → [4 deep specialists,
        |                                       3 auto-trained specialists,
        |                                       1 generalist]
        |                              ↓
        └──── feedback_loop.py ← unclaimed anomalous cases
```

- **Identify**: `app/identify/research_agent.py` — turns fraud-advisory summaries into taxonomy entries, and (live demo) synthesizes a brand-new entry when the feedback loop flags an emerging cluster.
- **Generate**: `app/generate/` — `tabular_generator.py` (structured session/transaction data), `llm_attacker.py` (Groq-scripted transcripts/ documents), `fidelity.py` (discriminator + KS-test scoring).
- **Defend**: `app/defend/` — `router.py` (TF-IDF + channel-match routing, no LLM in the hot path), 4 specialists in `specialists/`, `generalist.py` (IsolationForest fallback + novelty sensor), `feedback_loop.py` (the closed-loop mechanism).

### The 4 deep specialists (picked for real-world fraud volume)
1. **Voice-clone vishing** — Groq semantic scoring of call transcripts + rule-based call metadata
2. **Fake app / QR substitution** — deterministic registry verification (no ML needed)
3. **Account takeover** — GradientBoostingClassifier on session/behavioral features
4. **Synthetic identity / deepfake KYC** — Groq field-consistency check + image-artifact heuristic

### The 3 auto-trained specialists (and every future-discovered entry)
LLM-adaptive chat scams, agentic-AI prompt-injection abuse, AI-generated B2B invoice fraud. These are **not placeholders** — each gets a real `LogisticRegression` classifier, trained the moment its taxonomy entry exists, on synthetic data generated from an LLM-inferred feature profile (`app/generate/profile_inference.py`). Every one reports real precision/recall/F1/AUC via `/api/metrics`.

**The two tiers differ in depth of engineering, not in whether they work.** Deep specialists have hand-built logic tuned to their specific attack type (a Groq semantic prompt, a deterministic registry check, a model trained on curated feature distributions). Auto specialists get a generic-but-real pipeline: infer a plausible feature profile from the taxonomy description, generate synthetic legit-vs-attack data, train a classifier, cache it. **This is also exactly what happens when the closed loop discovers a brand-new pattern at runtime** — promotion isn't just "give it a name," it trains a working detector on the spot (`feedback_loop.py::_promote`). Nothing in this system is a dead end.

---
