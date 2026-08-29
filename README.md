# Orion — AI Defense Lab for Payment Security

*Mastercard Innovation Challenge @ GFF 2026*

A closed-loop red-team/blue-team system: **Identify** emerging GenAI payment
fraud patterns → **Generate** realistic synthetic attacks at scale →
**Defend** with a mixture of specialist detectors + a generalist safety net
that feeds discoveries back into Identify. Fully working, runs on free-tier
infrastructure, one API dependency (Groq).

---

## 1. Architecture recap

```
Identify (research agent + real web search)  →  Taxonomy Store (shared schema)
        ↑                              ↓
        |                    Generate (tabular + LLM-scripted content)
        |                              ↓
        |                    Defend: Router → [4 deep specialists,
        |                                       3 auto-trained specialists,
        |                                       1 generalist]
        |                              ↓
        |                    Policy engine (ALLOW/MONITOR/STEP_UP/BLOCK)
        |                              ↓
        └──── feedback_loop.py ← unclaimed anomalous cases (web-search-grounded)

                    Adversarial evolution (separate, on-demand):
                    generate → detect (round 1) → mutate to evade →
                    detect (round 2) → report whether it evaded
```

- **Identify**: `app/identify/research_agent.py` + `web_research.py` — real
  DuckDuckGo search (free, open-source `ddgs` package, no API key), run
  on-demand (button in the UI) or automatically when the closed loop is
  about to name a new pattern. **Not** a background scraper — see
  `web_research.py`'s docstring for exactly when this runs and why.
- **Generate**: `app/generate/` — `tabular_generator.py` (structured
  session/transaction data, profiles now grounded in real published
  statistics where they exist — see `RESEARCH.md`), `llm_attacker.py`
  (Groq-scripted transcripts/documents), `fidelity.py` (discriminator +
  KS-test scoring), `case_builder.py` (server-side case construction,
  used by the adversarial evolution endpoint).
- **Defend**: `app/defend/` — `router.py` (TF-IDF + channel-match routing,
  no LLM in the hot path), `pipeline.py` (the single shared detection
  flow used by both `/api/detect` and adversarial evolution), 4 deep
  specialists + auto-tier in `specialists/` and `auto_specialist.py`,
  `generalist.py` (IsolationForest fallback + novelty sensor),
  `policy.py` (risk score → ALLOW/MONITOR/STEP_UP/BLOCK), `adversarial.py`
  (red team vs blue team evolution loop), `feedback_loop.py` (the
  closed-loop promotion mechanism, now web-search-grounded).

### The 4 deep specialists (picked for real-world fraud volume)
1. **Voice-clone vishing** — Groq semantic scoring of call transcripts + rule-based call metadata
2. **Fake app / QR substitution** — deterministic registry verification (no ML needed)
3. **Account takeover** — GradientBoostingClassifier on session/behavioral features
4. **Synthetic identity / deepfake KYC** — Groq field-consistency check + image-artifact heuristic

### The 3 auto-trained specialists (and every future-discovered entry)
LLM-adaptive chat scams, agentic-AI prompt-injection abuse, AI-generated
B2B invoice fraud. These are **not placeholders** — each gets a real
`LogisticRegression` classifier, trained the moment its taxonomy entry
exists, on synthetic data generated from an LLM-inferred feature profile
(`app/generate/profile_inference.py`). Every one reports real precision/
recall/F1/AUC via `/api/metrics`.

**The two tiers differ in depth of engineering, not in whether they
work.** Deep specialists have hand-built logic tuned to their specific
attack type (a Groq semantic prompt, a deterministic registry check, a
model trained on curated feature distributions). Auto specialists get a
generic-but-real pipeline: infer a plausible feature profile from the
taxonomy description, generate synthetic legit-vs-attack data, train a
classifier, cache it. **This is also exactly what happens when the closed
loop discovers a brand-new pattern at runtime** — promotion isn't just
"give it a name," it trains a working detector on the spot
(`feedback_loop.py::_promote`). Nothing in this system is a dead end.

---

## 2. Tech stack (all free tier)

| Layer | Tool | Notes |
|---|---|---|
| LLM | **Groq API** — `openai/gpt-oss-20b` (fast) / `openai/gpt-oss-120b` (smart) | See §5 on model deprecation |
| Router | scikit-learn `TfidfVectorizer` + cosine similarity | No LLM call — latency-critical path |
| Account-takeover model | scikit-learn `GradientBoostingClassifier` | See §4 for why this replaced the original GNN plan |
| Generalist | scikit-learn `IsolationForest` | Trained on synthetic data at startup, cached to disk |
| Synthetic data | Custom numpy/scipy Gaussian-copula generator | See §4 for why this replaced SDV/CTGAN |
| Fidelity scoring | scikit-learn discriminator + `scipy.stats.ks_2samp` | |
| Backend | FastAPI + Uvicorn | |
| Frontend | React 19 + Vite + Tailwind + Recharts + lucide-react | |
| Hosting (backend) | Render free tier / Hugging Face Spaces (Docker) | |
| Hosting (frontend) | Vercel free tier | |

No paid API anywhere. No GPU required anywhere.

---

## 3. Running it locally

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your GROQ_API_KEY (optional, see below)
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for interactive API docs.

**No Groq key? The app still runs.** Every Groq call has a deterministic
offline fallback, so the whole pipeline — routing, specialists, generalist,
the closed loop — works end-to-end without any API key. Useful for local
dev, CI, or judges running it without setting up a key. Semantic scoring
quality is naturally better with a real key.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env            # points at http://localhost:8000 by default
npm run dev
```
Visit `http://localhost:5173`.

### Try the closed loop live
1. Open the **Simulate** tab, generate a couple of attacks.
2. Open **Agent Roster** — 4 deep specialists, 3 auto-trained specialists, all reporting real metrics.
3. Back in **Simulate**, click **Trigger pattern discovery** — this
   fast-forwards the organic feedback-loop process (which normally needs
   several real generalist-only catches to accumulate) so you can demo it
   in seconds. Watch a new specialist appear in the roster **with real
   precision/recall/F1/AUC already attached** — it trains on the spot,
   it isn't just a label.

### Do I need to "train" this before handing it to judges/evaluators?
No manual training step, ever. `ModelStore` and `AutoSpecialistStore` both
train (or load a cached model) automatically the moment the FastAPI app
starts — see the `auto_specialist_store.ensure_trained_for(...)` call at
the top of `main.py`. Anyone who clones this repo, runs `pip install` +
`uvicorn`, gets a fully working, fully trained system within seconds of
startup. Deploying to Render/Vercel is the same story — the training
happens as part of the container's first boot, not a separate step
someone has to remember to run. The only thing a real deployment adds
later is periodically retraining on real (not synthetic) data as it
accumulates — everything here is structured so that's a data-source swap,
not an architecture change.

---

## 4. Honest engineering tradeoffs (read this before a judge asks)

Three deliberate simplifications were made to keep this **deployable
anywhere on free-tier compute with zero GPU**, instead of chasing
theoretical fidelity that wouldn't actually run in a live demo:

**SDV/CTGAN → hand-rolled Gaussian-copula generator.**
SDV's neural synthesizers pull in PyTorch (2-4GB) and need real training
time per attack type. `app/generate/tabular_generator.py` implements the
same statistical idea (multivariate-normal copula + marginal transforms)
in ~150 lines of numpy/scipy — trains instantly, zero heavy deps. Swapping
in real SDV/CTGAN once you've pulled actual IEEE-CIS/PaySim data from
Kaggle is a drop-in replacement (same `generate(attack_id, n)` interface).

**Graph Neural Network → gradient-boosted trees on graph-adjacent features.**
The account-takeover specialist was originally scoped as a GNN over the
transaction network. PyTorch Geometric needs a labeled transaction graph
and heavier infra than free-tier deploy targets support. We use engineered
features (device-change, geo-velocity, tx-velocity — proxies for "this
session looks like part of a fast-moving takeover chain") fed into a
`GradientBoostingClassifier`, which trains in under a second. Upgrade path:
swap `model_store.predict_account_takeover()` for a PyG model with the
same signature once you have a labeled graph dataset.

**Deepfake detection → frequency-domain noise heuristic.**
Real deepfake-artifact detection needs a pretrained model with real
GPU-trained weights. `synthetic_identity.py`'s image check is a legitimate,
cheap, explainable heuristic (high-frequency noise-pattern consistency),
explicitly labeled as a proxy signal, not a production detector — see the
`image_check_type: "heuristic_proxy_not_production_deepfake_detector"`
field in every response. Upgrade path: swap in a pretrained HuggingFace
deepfake-detection checkpoint.

These are documented tradeoffs made under a free-tier, no-GPU, short
timeframe constraint — not omissions. Say so explicitly in the solution
walkthrough; judges read documented tradeoffs as engineering maturity, not
as a gap.

**Also simplified:** the Identify pillar runs on a curated set of seed
fraud-advisory summaries rather than a live scraper (`SEED_ADVISORIES` in
`research_agent.py`). Swapping in a live RBI/NPCI/CERT-In scraper is a
plumbing change, not an architecture change.

---

## 5. Groq model notes (important — check before the deadline)

Groq periodically retires models — `llama-3.1-8b-instant` and
`llama-3.3-70b-versatile` were both retired mid-2026, migrated to the
`openai/gpt-oss-*` family. Every model name in this repo lives in
**one place**: `backend/app/config.py` (overridable via `.env`), so a
future retirement is a two-line fix, not a codebase-wide find/replace.
Before your final submission, check
[console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations)
and confirm `GROQ_MODEL_FAST` / `GROQ_MODEL_SMART` are still current.

**Rate limits**: Groq's free tier is roughly 30 requests/minute. This repo
self-limits to 20 rpm (`GROQ_MAX_RPM` in `.env`) with exponential backoff
on 429s and response caching (identical prompt+model → cached result), so
a live demo with judges asking questions won't trip the limit.

---

## 6. Deployment (free tier)

**Backend → Render or Hugging Face Spaces (Docker)**
- Push `backend/` as its own repo/directory.
- Render: New Web Service → point at `backend/`, build command
  `pip install -r requirements.txt`, start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Set `GROQ_API_KEY` (and other `.env` vars) in the platform's env var UI.

**Frontend → Vercel**
- Push `frontend/` as its own repo/directory.
- Framework preset: Vite. Set `VITE_API_URL` to your deployed backend URL.

Both platforms' free tiers are sufficient for a hackathon demo's traffic.

---

## 7. Repo structure

```
backend/
  app/
    main.py                    # FastAPI app, all routes
    config.py                  # env config incl. Groq model names
    groq_client.py             # rate-limited, cached, retrying Groq wrapper
    taxonomy.py                # shared taxonomy store (the closed-loop spine)
    identify/research_agent.py
    generate/
      tabular_generator.py
      llm_attacker.py
      fidelity.py
    defend/
      router.py
      generalist.py
      model_store.py           # trains/caches ATO + generalist models
      registry.py               # attack_id -> deep vs auto tier routing
      auto_specialist.py         # generic trained-classifier pipeline for the auto tier
      feature_utils.py           # shared feature extraction, used by generalist/ATO/auto
      feedback_loop.py          # the closed-loop promotion mechanism (trains a real model)
      specialists/
        vishing.py
        fake_app_qr.py
        account_takeover.py
        synthetic_identity.py
    data/
      seed_taxonomy.json
      verified_merchants.json
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx                     # shell, nav, health polling
    api.js                      # backend client
    components/
      RiskGauge.jsx              # signature UI element
      ShieldMark.jsx
      CaseDetailDrawer.jsx
    pages/
      LiveFeed.jsx
      Simulate.jsx
      AgentRoster.jsx
      Metrics.jsx
  .env.example
README.md                       # this file
```

---

## 8. If a page hangs on "loading…"

That almost always means the frontend can't reach the backend. Every page
now shows a clear error card with a Retry button instead of hanging
silently, but here's how to confirm the cause fast:

1. **Is the backend actually running?** `curl http://localhost:8000/api/health`
   should return `{"status":"ok",...}`. If it doesn't, start it:
   `cd backend && uvicorn app.main:app --reload --port 8000`.
2. **Is the frontend pointed at the right URL?** Check `frontend/.env` —
   `VITE_API_URL` must match wherever the backend is actually listening.
   If you deployed the backend, this needs to be the deployed URL, not
   `localhost`.
3. **Browser console** (F12 → Console/Network tab) will show the exact
   failed request and status code — a CORS error, a connection-refused,
   or a 500 all look different there and each points to a different fix.

## 9. What to say in the solution walkthrough deck

Map straight onto the judging criteria:

- **Diversity**: 7-entry taxonomy across voice/QR/session/onboarding/chat/
  agent/B2B channels, self-expanding via the closed loop, each new
  discovery grounded in a real web search rather than pure LLM guess.
- **Fidelity**: `/api/fidelity/{attack_id}` reports discriminator-AUC-based
  fidelity score + per-feature KS-test. Profiles are grounded in real
  published statistics where they exist (NPCI ticket sizes, RBI-linked
  fraud-loss figures) — see `RESEARCH.md` for exactly what's cited vs
  estimated. Say this explicitly; overclaiming here is the easiest way to
  lose credibility with a technical judge.
- **Detection efficacy**: `/api/metrics` reports precision/recall/F1/AUC
  per model. **Say the honest caveat out loud**: both train and test data
  come from the same synthetic generator, so these numbers show the model
  learned its own generator's distribution, not proven real-world
  generalization. That's exactly what `/api/adversarial/evolve` is for —
  a genuine out-of-distribution stress test where the red team tries to
  fool the blue team's own detector.
- **Novelty**: the closed loop (generalist-only catches → web-search-
  grounded discovery → new specialist trained on the spot) plus the
  adversarial evolution loop (red team explicitly attacks its own blue
  team, live) are the two things most teams won't have built.
- **Real-world feasibility**: router has zero LLM calls in the hot path,
  every verdict ships explainable reason codes AND a policy action
  (ALLOW/MONITOR/STEP_UP/BLOCK — detection alone isn't mitigation),
  rate-limiting/caching keeps Groq usage production-plausible, and the
  honest-limitations sections above and in `RESEARCH.md` show you know
  exactly where the gaps are and how to close them.

## 10. Known next-phase work (say this proactively, don't wait to be asked)

- **Attack Intelligence Graph**: right now each taxonomy entry is a flat
  card. A judge may want to see attack family → mechanism → payment
  surface → prerequisites → observable signals as an explicit structure.
  The schema supports adding these fields; the UI doesn't visualize them
  as a graph yet.
- **Cross-generator / held-out evaluation**: partially built now (§11) —
  the strongest possible extension is real historical incident data from
  an actual deployment, not synthetic perturbation.
- **Scheduled research**: `web_research.py` is on-demand by design for
  demo predictability. A production version would add a real scheduler
  (APScheduler or cron) running research cycles every few hours.
- **Objective-driven adversarial mutation**: the current red team tries
  one mutation strategy per round (rewrite text, or nudge features toward
  baseline). A stronger version would generate several candidate
  mutations and report the one that most reduces detector confidence —
  closer to a real optimization search than a single heuristic pass.

## 11. What's been added since the first working version — read this before assuming it's stale

Three real reviews of this project converged hard on the same critique:
**in-distribution metrics don't prove real-world generalization, and the
one adversarial data point (Voice-Clone Vishing losing every Arena round)
was the most important evidence on screen, not a bug to hide.** Here's
what changed in response, concretely:

**Vishing hardened, with the fix verified before shipping it.** The
original specialist weighted Groq's semantic scam-language scoring at
65% and call metadata (VOIP-masking, duration) at 35%. Since the red
team's mutation can only rewrite the transcript, not the metadata, a
clean rewrite alone was usually enough to evade detection. Rebalanced to
45%/55% and added a floor: when metadata alone strongly suggests fraud,
the score can't drop below 0.42 regardless of how clean the text reads —
`app/defend/specialists/vishing.py`. Verified with an explicit before/
after calculation on the same scenario (old weights: 0.28, evaded; new
weights: 0.41, caught) before merging — see the module docstring. **Not
yet re-validated against a live Groq key** — the offline fallback can't
reproduce the exact evasion dynamic that was observed; re-run the vishing
Arena battle with your own key and see what actually happens.

**Three evaluation regimes, not one headline F1** —
`app/defend/evaluation_regimes.py`, `GET /api/metrics/evaluation-regimes/{attack_id}`.
IID (same distribution as training — expect this to look best, it's the
easiest test), cross-generator (same trained model tested against a
perturbed distribution, or real calibrated data if available), and
adversarial-OOD (reuses the Arena's red-team mechanism). Surfaced in the
Metrics page's Robustness section. A model strong on IID but weak on the
other two learned its own generator's shape, not fraud in general — that
gap is the finding, not a flaw in the report.

**Governance gate for auto-discovered specialists** —
`app/defend/governance.py`. A newly-discovered pattern no longer goes
straight to "active." It's trained, then must pass a gate (precision ≥
0.60, recall ≥ 0.60, FPR ≤ 0.35, and survive at least half of a 3-round
adversarial battle) before its `lifecycle_stage` becomes `"promoted"` and
the router will send it live traffic. Entries that fail stay `"shadow"` —
visible in Agent Roster with the specific reasons they failed, trained
and testable, but excluded from live routing (`router.py` only routes to
`"promoted"` entries). The gate's thresholds are illustrative prototype
values, not a risk-committee-defined production standard — say so if
asked.

**Real-data calibration path, actually built, not just documented** —
`scripts/calibrate_from_real_data.py`. Download PaySim from Kaggle
(free account, `ntnu-testimon/paysim1`), run the script against the CSV,
restart the backend. It calibrates `legit` and `account_takeover`'s
`hour_of_day`, `amount_inr`, and `tx_velocity_10min` against real
statistics; `device_change`, `geo_velocity_kmh`, and
`login_failed_attempts` have no PaySim signal and stay as Orion's
estimates — the script does not invent numbers for what the dataset
doesn't cover. `GET /api/generate/calibration-status` reports whether
calibration is active. Claude could not run this script itself (Kaggle
isn't reachable from the dev sandbox) — it was tested against a
synthetic PaySim-*shaped* CSV to confirm the mechanics work, not against
the real dataset. Run it yourself and check the output.

**Fidelity wording corrected.** "High fidelity" now reads "high
distributional fidelity ... NOT a claim of matching real-world data
unless that reference is itself real" — `app/generate/fidelity.py`. A
review correctly pointed out that "hard to distinguish from real" was
overclaiming when the reference set is itself synthetic.

**Generalist's low recall is now explained as intentional**, not left to
read as a weak model — its job is breadth-of-novelty-sensing, not primary
detection. See the Metrics page.
