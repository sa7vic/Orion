# Research grounding

This documents exactly what in Orion's synthetic data is backed by a real,
citable source versus what is an informed estimate. The goal is that
nothing here is asserted as "real-world calibrated" without saying
precisely which part is and which isn't.

## What's genuinely grounded (real published numbers)

| Value used | Source | What it actually says |
|---|---|---|
| Legit avg UPI ticket size ≈ Rs 1,350 | NPCI FY2025-26 data (via PIB/industry reporting, 2026) | Rs 314 lakh crore in transaction value over 24,162 crore transactions ≈ Rs 1,300-1,400 average; 86% of P2M transactions fall in the Rs 0-500 band |
| QR/fake-app fraud skews to sub-Rs-500 amounts | 2026 UPI fraud trend reporting | Explicitly flags micro-transactions under Rs 500 as an emerging tactic specifically to stay under bank alert thresholds |
| Account-takeover / vishing amount magnitude (Rs 50k-5L range) | 2026 UPI fraud trend reporting citing RBI-linked data | "Average loss: Rs 50,000-Rs 5 lakh per merchant before detection" |
| Synthetic fraud-rate benchmark: real fraud is ~0.1-0.5% of transactions, not 50/50 | PaySim (Lopez-Rojas et al.) — 6.36M transactions, 0.13% fraud; a widely-cited credit-card fraud benchmark — 284,807 transactions, 0.17% fraud | Used to explicitly flag that Orion's balanced synthetic training set does NOT represent real-world class imbalance — see the limitation note in `tabular_generator.py` |
| UPI fraud overall scale | RBI Annual Report FY2024-25 / Lok Sabha responses, 2026 | Digital payment frauds ~56.5% of all reported banking frauds; UPI fraud cases rose from ~6.32 lakh (FY24-25) to ~10.64 lakh (FY25-26 through Nov), value ~Rs 485-805 crore |

## What's directionally grounded, magnitude estimated

Account-takeover behavioral signals — device change, geo-velocity (impossible
travel speed between logins), transaction velocity, failed login attempts —
are confirmed as industry-standard fraud signals by Stripe, FraudNet, and
Veriff's public documentation on velocity checks and geo-velocity detection.
**What isn't public:** the actual numeric thresholds fraud vendors use
internally (that's their product). So the *direction* ("account takeover
shows elevated geo-velocity") is real and cited; the specific mean/std
values assigned in `FEATURE_PROFILES` are an informed estimate, not a
number pulled from a published dataset.

## What's LLM-inferred, not researched at all (be honest about this in the walkthrough)

The auto-tier taxonomy entries (and any entry the closed loop discovers)
get their feature profile from `profile_inference.py`, which asks Groq to
qualitatively estimate feature direction from the taxonomy description.
As of this update, `research_agent.py`'s `synthesize_new_attack_id()` now
runs a real web search (`web_research.py`, DuckDuckGo via the `ddgs`
package) using the cluster summary as the query, and feeds the actual
search snippets into that prompt — so newly-discovered patterns are
grounded in real search results, not pure LLM free-association. Existing
entries can be refreshed the same way via `POST /api/identify/research/{attack_id}`.

**What this does NOT do:** turn search snippets into calibrated numeric
feature distributions. The LLM still estimates elevated/normal/reduced
qualitatively from the combination of the taxonomy description and
whatever real snippets came back. That's a real improvement over pure
invention, but it's not the same rigor as the grounded seed profiles
above — say so if asked.

## Known evaluation artifact: account-takeover is suspiciously clean

`/api/metrics/threshold-curve/account_takeover` shows 98% recall / 0% false
positive rate even at a 0.95 decision threshold — the classifier separates
the two synthetic classes almost perfectly across the entire threshold
range. This is a signal that `account_takeover`'s `FEATURE_PROFILES` in
`tabular_generator.py` are currently too *cleanly* separated from the
legit profile (real fraud overlaps with legitimate behavior far more than
this). Compare against the auto-tier `llm_adaptive_chat_scam` curve, which
shows a much more believable tradeoff (85%→16% recall as threshold moves
0.3→0.95). Worth tightening the account-takeover legit/attack profile gap
before presenting the 1.00/1.00/1.00 result as anything more than "the
classifier learned this particular synthetic boundary well" — say this
proactively rather than let a judge find it first.

## The Assurance layer: RBI FREE-AI Recommendation 20 (verified, corrected)

Orion's Arena includes a "Run audit" feature that operationalizes a specific,
named recommendation from RBI's FREE-AI Committee Report (published 13
August 2025 — "Framework for Responsible and Ethical Enablement of
Artificial Intelligence"):

> **Recommendation 20 — "Red Teaming"** (Protection pillar, Medium term):
> "Set up structured red teaming across the AI lifecycle, proportionate to
> risk — more frequent for high-risk models. Include trigger-based red
> teaming for evolving threats."

A related recommendation, **24 ("AI Audit Framework")**, calls for periodic,
independent, risk-tiered audits of AI models — Orion's retained round-level
detail is structured to support this, not to replace it.

**Correction trail, kept here deliberately:** an earlier pass at this
citation attributed the red-teaming language to a different pillar
("Assurance") with slightly paraphrased wording, based on a single source.
A subsequent independent review flagged the correct recommendation number
and pillar; that claim was then verified here against 6 independent
secondary sources (a CISO-focused Medium analysis, Mondaq legal/compliance
commentary, Drishti IAS current-affairs summary, Lexplosion Solutions legal
analysis, a Solytics Partners industry blog, and spog.ai's framework
summary) before being adopted. All six independently describe the same
recommendation number (20), the same pillar (Protection), and materially
the same wording ("structured... proportionate to risk... trigger-based for
evolving threats"). **None of these are RBI's primary PDF directly** —
verify against the primary source before using this citation in a formal
submission.

**Wording discipline, non-negotiable:** this is a committee report
recommendation, not binding RBI regulation. Say "Orion operationalizes
Recommendation 20" — never "Orion satisfies an RBI mandate" or "Orion makes
you compliant." Orion is not an auditor; it generates evidence a regulated
entity's own governance process would use.

**What the Assurance report deliberately does NOT do:** assign a letter
grade, star rating, or pass/fail threshold. An earlier draft of this
feature did exactly that (an invented A–F scale over the real blue-win-rate
number) and was correctly rejected as "made up out of thin air" — there is
no published industry standard for grading fraud-model adversarial
robustness. The report shows the real measured numbers only; interpreting
what counts as acceptable is left to the regulated entity's own risk
appetite, per FREE-AI's own governance model.

## Sources referenced

- Lopez-Rojas, E. et al. "PaySim: A financial mobile money simulator for
  fraud detection." (2016) — via ResearchGate and multiple citing papers.
- NPCI / PIB press materials on UPI's 10-year statistics (2026).
- RBI Annual Report FY2024-25 digital payment fraud figures (via Business
  Standard, LocalCircles survey coverage, Lok Sabha responses, 2025-2026).
- "Top UPI Frauds Trends in India 2026" — industry blog aggregating RBI
  circulars and NCRB data; treat as secondary reporting, not a primary
  RBI publication.
- Stripe, FraudNet, and Veriff public documentation on velocity checks
  and geo-velocity fraud detection.
- A widely-used credit-card fraud benchmark dataset (284,807 transactions,
  492 fraud cases, ~0.17% fraud rate) — cited for class-imbalance context.