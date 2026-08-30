import { useEffect, useState } from "react";
import { Play, Zap, Loader2, ChevronRight, Sparkles, Search, Swords, ExternalLink, ShieldAlert, ArrowRight } from "lucide-react";
import api from "../api";
import { tierColor } from "../components/RiskGauge";
import RiskGauge from "../components/RiskGauge";
import ErrorState from "../components/ErrorState";

const CHANNEL_LABEL = {
  voice_call: "Voice call",
  qr_or_app: "QR / App",
  session: "Session",
  onboarding: "Onboarding",
  chat: "Chat",
  agent_api: "Agent API",
  business_payment: "B2B payment",
};

const POLICY_COLOR = {
  ALLOW: "text-safe bg-safe/10 border-safe/30",
  MONITOR: "text-info bg-info/10 border-info/30",
  STEP_UP: "text-warn bg-warn/10 border-warn/30",
  BLOCK: "text-danger bg-danger/10 border-danger/30",
};

// Builds the /api/detect payload shape each specialist expects, from the
// Generate pillar's output. Mirrors backend/app/generate/case_builder.py --
// if you change one, change the other.
function buildCasePayload(attackId, record, unstructured) {
  switch (attackId) {
    case "vishing_relative_emergency":
      return {
        transcript: unstructured?.transcript || "No transcript generated.",
        metadata: {
          voip_masked: record.device_change === 1,
          call_duration_seconds: Math.max(20, 200 - record.tx_velocity_10min * 25),
          caller_reputation: record.login_failed_attempts > 1 ? "flagged" : "unknown",
        },
      };
    case "fake_app_qr_substitution": {
      const fraudulent = Math.random() > 0.35;
      return {
        vpa: fraudulent ? "chaicorner@okicici" : "citymart@okhdfc",
        qr_hash: fraudulent ? "ffff0000" : "e5f6a7b8",
        metadata: {
          hour_of_day: record.hour_of_day,
          device_change: record.device_change,
          geo_velocity_kmh: record.geo_velocity_kmh,
          tx_velocity_10min: record.tx_velocity_10min,
          login_failed_attempts: record.login_failed_attempts,
          amount_inr: record.amount_inr,
        },
      };
    }
    case "account_takeover":
      return {
        session_features: {
          hour_of_day: record.hour_of_day,
          device_change: record.device_change,
          geo_velocity_kmh: record.geo_velocity_kmh,
          tx_velocity_10min: record.tx_velocity_10min,
          login_failed_attempts: record.login_failed_attempts,
          amount_inr: record.amount_inr,
        },
      };
    case "synthetic_identity_kyc":
      return {
        application_fields: unstructured?.application_fields || { name: "Unknown" },
        document_fields: unstructured?.document_fields || { name: "Unknown" },
      };
    default:
      return {
        summary: unstructured?.chat || `Simulated ${attackId} case`,
        metadata: {
          hour_of_day: record.hour_of_day,
          device_change: record.device_change,
          geo_velocity_kmh: record.geo_velocity_kmh,
          tx_velocity_10min: record.tx_velocity_10min,
          login_failed_attempts: record.login_failed_attempts,
          amount_inr: record.amount_inr,
        },
      };
  }
}

export default function Simulate({ onCaseCreated }) {
  const [taxonomy, setTaxonomy] = useState([]);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const loadTaxonomy = () => {
    setLoadError(null);
    api.taxonomy()
      .then((r) => {
        setTaxonomy(r.entries);
        setSelected(r.entries[0]?.attack_id || null);
      })
      .catch((e) => setLoadError(e.message));
  };

  useEffect(() => { loadTaxonomy(); }, []);

  const selectedEntry = taxonomy.find((t) => t.attack_id === selected);

  const run = async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const sim = await api.simulate(selected, 1);
      const record = sim.tabular_records[0];
      const entry = taxonomy.find((t) => t.attack_id === selected);
      const casePayload = buildCasePayload(selected, record, sim.unstructured_sample);
      const detection = await api.detect({
        channel: entry?.channel,
        case: casePayload,
      });
      setResult({ sim, detection });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  // --- Closed-loop discovery demo ---
  const [discovering, setDiscovering] = useState(false);
  const [discoverResult, setDiscoverResult] = useState(null);

  const triggerDiscovery = async () => {
    setDiscovering(true);
    setDiscoverResult(null);
    try {
      const autoEntry = taxonomy.find((t) => t.specialist_tier === "auto");
      const channel = autoEntry?.channel || "chat";
      const res = await api.forcePromote(channel, [
        "bot built rapport over several messages then asked for UPI ID citing a fake refund deadline",
        "escalating urgency chat impersonating support, requested one-time password to 'verify' account",
        "chat script adapted tone from friendly to threatening when victim hesitated",
      ]);
      setDiscoverResult(res.promoted);
      api.taxonomy().then((r) => setTaxonomy(r.entries)).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setDiscovering(false);
    }
  };

  // --- Real-time research on the selected pattern ---
  const [researching, setResearching] = useState(false);
  const [researchResult, setResearchResult] = useState(null);

  const researchThis = async () => {
    if (!selected) return;
    setResearching(true);
    setResearchResult(null);
    try {
      const res = await api.researchPattern(selected);
      setResearchResult(res);
      api.taxonomy().then((r) => setTaxonomy(r.entries)).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setResearching(false);
    }
  };

  // --- Adversarial evolution: red team attacks the blue team's own detector ---
  const [evolving, setEvolving] = useState(false);
  const [evolveResult, setEvolveResult] = useState(null);

  const evolveThis = async () => {
    if (!selected) return;
    setEvolving(true);
    setEvolveResult(null);
    try {
      const res = await api.evolveAttack(selected);
      setEvolveResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setEvolving(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {loadError && <ErrorState message={loadError} onRetry={loadTaxonomy} />}
      {!loadError && (
      <>
      <div>
        <h2 className="font-display text-xl font-semibold">Simulate an attack</h2>
        <p className="text-sm text-muted mt-1">
          Generate a synthetic attack from the taxonomy, then watch it flow through routing and detection in real time.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {taxonomy.map((t) => (
          <button
            key={t.attack_id}
            onClick={() => { setSelected(t.attack_id); setResearchResult(null); setEvolveResult(null); }}
            className={`text-left p-3.5 rounded-xl border transition-colors ${
              selected === t.attack_id
                ? "border-accent bg-accent/10"
                : "border-border bg-panel hover:border-accentDim"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span
                className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider ${
                  t.specialist_tier === "deep"
                    ? "bg-safe/15 text-safe"
                    : "bg-accent/15 text-accent"
                }`}
              >
                {t.specialist_tier}
              </span>
              <span className="text-[10px] font-mono text-faint">{CHANNEL_LABEL[t.channel] || t.channel}</span>
            </div>
            <div className="text-sm font-medium leading-snug">{t.display_name}</div>
          </button>
        ))}
      </div>

      {/* Info panel for the selected pattern */}
      {selectedEntry && (
        <div className="bg-panel2 border border-border rounded-xl p-4 space-y-3">
          <div>
            <div className="text-sm font-medium">{selectedEntry.display_name}</div>
            <p className="text-xs text-muted mt-1 leading-relaxed">{selectedEntry.description}</p>
          </div>
          {selectedEntry.social_engineering_pattern && selectedEntry.social_engineering_pattern !== "n/a" && (
            <div className="text-xs">
              <span className="text-faint font-mono uppercase tracking-wider text-[10px]">Social engineering: </span>
              <span className="text-muted">{selectedEntry.social_engineering_pattern}</span>
            </div>
          )}
          {selectedEntry.technical_signature?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {selectedEntry.technical_signature.map((sig) => (
                <span key={sig} className="text-[10px] font-mono text-faint bg-panel border border-border px-2 py-0.5 rounded-full">
                  {sig}
                </span>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            <button
              onClick={researchThis}
              disabled={researching}
              className="flex items-center gap-1.5 text-[11px] font-mono text-info border border-info/40 px-2.5 py-1 rounded-lg hover:bg-info/10 disabled:opacity-50 transition-colors"
            >
              {researching ? <Loader2 size={11} className="animate-spin" /> : <Search size={11} />}
              Research this pattern
            </button>
            <button
              onClick={evolveThis}
              disabled={evolving}
              className="flex items-center gap-1.5 text-[11px] font-mono text-warn border border-warn/40 px-2.5 py-1 rounded-lg hover:bg-warn/10 disabled:opacity-50 transition-colors"
            >
              {evolving ? <Loader2 size={11} className="animate-spin" /> : <Swords size={11} />}
              Evolve this attack (red vs blue)
            </button>
            {selectedEntry.last_researched_at && (
              <span className="text-[10px] font-mono text-faint self-center">
                last researched {new Date(selectedEntry.last_researched_at).toLocaleString()}
              </span>
            )}
          </div>

          {researchResult && (
            <div className="pt-2 border-t border-border/60 space-y-2">
              {researchResult.research_sources?.length > 0 ? (
                <>
                  <div className="text-[10px] font-mono text-faint uppercase tracking-wider">
                    {researchResult.research_sources.length} live source(s) found
                  </div>
                  {researchResult.research_sources.map((s, i) => (
                    <a
                      key={i}
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-start gap-1.5 text-xs text-info hover:underline"
                    >
                      <ExternalLink size={11} className="mt-0.5 shrink-0" />
                      <span>{s.title}</span>
                    </a>
                  ))}
                </>
              ) : (
                <div className="text-xs text-faint">
                  No live search results this time (search may be rate-limited, or no clear internet
                  match) — this is reported honestly rather than papered over.
                </div>
              )}
            </div>
          )}

          {evolveResult && (
            <div className="pt-2 border-t border-border/60 space-y-3">
              <div className="text-[10px] font-mono text-faint uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert size={12} /> Adversarial evolution: red team vs blue team
              </div>
              {!evolveResult.round_2 ? (
                <div className="text-xs text-muted">
                  {evolveResult.mutation?.reason || "Round 1 wasn't caught -- nothing to evade."}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                    <div className="bg-panel border border-border rounded-lg p-3 text-center">
                      <div className="text-[9px] font-mono text-faint uppercase">Round 1 — original attack</div>
                      <div className="text-2xl font-mono font-bold mt-1" style={{ color: tierColor(evolveResult.round_1.final_risk_score) }}>
                        {evolveResult.round_1.final_risk_score.toFixed(2)}
                      </div>
                      <div className="text-[10px] font-mono text-faint mt-0.5">
                        {evolveResult.round_1.policy?.action || evolveResult.round_1.risk_tier?.toUpperCase()}
                      </div>
                    </div>
                    <ArrowRightSmall evaded={evolveResult.mutation.evaded} />
                    <div className="bg-panel border border-border rounded-lg p-3 text-center">
                      <div className="text-[9px] font-mono text-faint uppercase">Round 2 — mutated attack</div>
                      <div className="text-2xl font-mono font-bold mt-1" style={{ color: tierColor(evolveResult.round_2.final_risk_score) }}>
                        {evolveResult.round_2.final_risk_score.toFixed(2)}
                      </div>
                      <div className="text-[10px] font-mono text-faint mt-0.5">
                        {evolveResult.round_2.policy?.action || evolveResult.round_2.risk_tier?.toUpperCase()}
                      </div>
                    </div>
                  </div>

                  <div
                    className={`text-center text-xs font-mono font-bold py-2 rounded-lg border ${
                      evolveResult.mutation.evaded
                        ? "text-danger bg-danger/10 border-danger/30"
                        : "text-safe bg-safe/10 border-safe/30"
                    }`}
                  >
                    {evolveResult.mutation.evaded
                      ? `⚠ EVASION SUCCESSFUL — policy downgraded to ${evolveResult.round_2.policy?.action || "ALLOW/MONITOR"}`
                      : `✓ MITIGATION HELD — policy enforced ${evolveResult.round_2.policy?.action || "STEP_UP/BLOCK"}`}
                  </div>

                  <div className="text-xs text-muted">
                    <span className="text-faint font-mono uppercase text-[10px]">Mutation strategy: </span>
                    {evolveResult.mutation.description}
                    {" — score moved by "}
                    <span className="font-mono">{evolveResult.mutation.score_delta}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <button
        onClick={run}
        disabled={busy || !selected}
        className="flex items-center gap-2 bg-accent text-base font-semibold text-sm px-5 py-2.5 rounded-lg hover:bg-accent/90 disabled:opacity-50 transition-colors"
      >
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
        Generate &amp; run detection
      </button>

      {error && <div className="text-sm text-danger font-mono">{error}</div>}

      {result && (
        <div className="bg-panel border border-border rounded-xl p-5 space-y-5 animate-[fadeIn_0.3s_ease]">
          <div className="flex items-center gap-4">
            <RiskGauge score={result.detection.final_risk_score} size={72} />
            <div className="flex-1">
              <div
                className="text-lg font-display font-semibold"
                style={{ color: tierColor(result.detection.final_risk_score) }}
              >
                {result.detection.risk_tier?.toUpperCase()} RISK
              </div>
              <div className="text-xs text-muted font-mono mt-0.5">
                routed to: {result.detection.routing?.attack_id
                  ? (taxonomy.find((t) => t.attack_id === result.detection.routing.attack_id)?.display_name || result.detection.routing.attack_id)
                  : "generalist"} · confidence{" "}
                {result.detection.routing?.confidence?.toFixed(2)}
              </div>
            </div>
            {result.detection.policy && (
              <span className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-lg border ${POLICY_COLOR[result.detection.policy.action] || ""}`}>
                {result.detection.policy.action.replace("_", "-")}
              </span>
            )}
          </div>

          {/* Specialist vs generalist verdict split */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-panel2 rounded-lg p-3 border border-border">
              <div className="text-[10px] font-mono text-faint uppercase tracking-wider">Specialist verdict</div>
              <div className="text-base font-mono font-semibold mt-1">
                {result.detection.specialist_result ? result.detection.specialist_result.risk_score.toFixed(2) : "—"}
              </div>
            </div>
            <div className="bg-panel2 rounded-lg p-3 border border-border">
              <div className="text-[10px] font-mono text-faint uppercase tracking-wider">Generalist verdict</div>
              <div className="text-base font-mono font-semibold mt-1">
                {result.detection.generalist_result.risk_score.toFixed(2)}
              </div>
            </div>
          </div>

          {result.sim.unstructured_sample && (
            <div>
              <div className="text-[10px] font-mono text-faint uppercase tracking-wider mb-2">Generated content</div>
              <pre className="text-xs font-mono text-muted bg-panel2 border border-border rounded-lg p-3 whitespace-pre-wrap">
                {JSON.stringify(result.sim.unstructured_sample, null, 2)}
              </pre>
            </div>
          )}

          <div>
            <div className="text-[10px] font-mono text-faint uppercase tracking-wider mb-2">Reasons</div>
            <ul className="space-y-1">
              {result.detection.final_reasons?.map((r, i) => (
                <li key={i} className="text-xs text-muted flex gap-2">
                  <ChevronRight size={12} className="text-accent mt-0.5 shrink-0" />
                  {r}
                </li>
              ))}
            </ul>
          </div>

          <button
            onClick={() => onCaseCreated?.()}
            className="text-xs font-mono text-accent hover:underline"
          >
            View in live feed →
          </button>
        </div>
      )}

      <div className="border-t border-border pt-6">
        <div className="flex items-start gap-3 bg-panel2 border border-accent/20 rounded-xl p-4">
          <Sparkles size={18} className="text-accent mt-0.5 shrink-0" />
          <div className="flex-1">
            <div className="text-sm font-medium">Closed-loop demo: discover a new pattern</div>
            <p className="text-xs text-muted mt-1 leading-relaxed">
              In production this fires automatically once the generalist repeatedly flags a cluster of
              cases no specialist confidently claims. This button fast-forwards that process for the demo —
              it runs a real web search grounded in the sample cluster, feeds that to the Identify agent to
              name the pattern, then trains a real classifier for it on the spot (auto tier).
            </p>
            <button
              onClick={triggerDiscovery}
              disabled={discovering}
              className="mt-3 flex items-center gap-2 text-xs font-mono font-semibold text-accent border border-accent/40 px-3 py-1.5 rounded-lg hover:bg-accent/10 disabled:opacity-50 transition-colors"
            >
              {discovering ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
              Trigger pattern discovery
            </button>
            {discoverResult && (
              <div className="mt-3 text-xs bg-accent/5 border border-accent/20 rounded-lg p-3 space-y-2">
                <div className="text-accent font-mono font-semibold">
                  ◆ New specialist created: {discoverResult.display_name}
                </div>
                <div className="text-muted">{discoverResult.description}</div>
                {discoverResult.training_metrics && (
                  <div className="flex gap-3 font-mono text-[10px] text-faint pt-1 border-t border-accent/10">
                    <span>precision {discoverResult.training_metrics.precision}</span>
                    <span>recall {discoverResult.training_metrics.recall}</span>
                    <span>f1 {discoverResult.training_metrics.f1}</span>
                    <span>auc {discoverResult.training_metrics.auc}</span>
                  </div>
                )}
                {discoverResult.research_sources?.length > 0 && (
                  <div className="pt-1 border-t border-accent/10 text-[10px] text-faint">
                    Grounded in {discoverResult.research_sources.length} live search result(s).
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      </>
      )}
    </div>
  );
}

function ArrowRightSmall({ evaded }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <ArrowRight size={20} className={evaded ? "text-danger" : "text-safe"} />
      <span className={`text-[9px] font-mono ${evaded ? "text-danger" : "text-safe"}`}>
        {evaded ? "evaded" : "held"}
      </span>
    </div>
  );
}
