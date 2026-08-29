import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Loader2, Sliders, Swords } from "lucide-react";
import api from "../api";
import ErrorState from "../components/ErrorState";
import { tierColor } from "../components/RiskGauge";

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);
  const [taxonomy, setTaxonomy] = useState([]);
  const [fidelityResults, setFidelityResults] = useState({});
  const [loadingFidelity, setLoadingFidelity] = useState(false);
  const [error, setError] = useState(null);

  const load = () => {
    setError(null);
    Promise.all([api.metrics(), api.taxonomy()])
      .then(([m, t]) => {
        setMetrics(m);
        setTaxonomy(t.entries);
        runAllFidelity(t.entries); // auto-run so this page never shows an empty "—" by default
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => { load(); }, []);

  const runAllFidelity = async (entries) => {
    setLoadingFidelity(true);
    const results = {};
    for (const t of entries || taxonomy) {
      try {
        results[t.attack_id] = await api.fidelity(t.attack_id);
      } catch {
        /* skip */
      }
    }
    setFidelityResults(results);
    setLoadingFidelity(false);
  };

  if (error && !metrics) return <ErrorState message={error} onRetry={load} />;
  if (!metrics) return <div className="text-faint text-sm font-mono">loading metrics…</div>;

  const deepEntries = Object.entries(metrics.deep_tier_metrics || {});
  const autoEntries = Object.entries(metrics.auto_tier_metrics || {});
  const chartData = [...deepEntries, ...autoEntries].map(([name, m]) => ({
    name,
    precision: m.precision,
    recall: m.recall,
    f1: m.f1,
  }));

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h2 className="font-display text-xl font-semibold">Detection efficacy &amp; fidelity</h2>
        <p className="text-sm text-muted mt-1">{metrics.note}</p>
      </div>

      <div>
        <div className="text-xs font-mono text-faint uppercase tracking-wider mb-3">Deep tier</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {deepEntries.map(([name, m]) => (
            <MetricCard key={name} name={name} m={m} accentClass="text-safe" />
          ))}
        </div>
      </div>

      {metrics.generalist_metrics && (
        <div>
          <div className="text-xs font-mono text-faint uppercase tracking-wider mb-3">Generalist (always-on fallback)</div>
          <p className="text-[10px] text-muted mb-2 max-w-lg">
            Lower recall here is intentional, not a weak model — the generalist's job is breadth-of-novelty
            sensing (catch things no specialist recognizes yet), not primary detection. It's tuned toward
            not crying wolf on legitimate traffic, at the cost of missing subtler anomalies specialists
            would catch. See per-specialist recall above for actual detection performance.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MetricCard name="generalist" m={metrics.generalist_metrics} accentClass="text-info" />
          </div>
        </div>
      )}

      <div>
        <div className="text-xs font-mono text-faint uppercase tracking-wider mb-3">Auto tier</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {autoEntries.map(([name, m]) => (
            <MetricCard key={name} name={name} m={m} accentClass="text-accent" />
          ))}
        </div>
      </div>

      {chartData.length > 0 && (
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="text-xs font-mono text-faint uppercase tracking-wider mb-4">Precision / Recall / F1 — all specialists</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#242438" vertical={false} />
              <XAxis dataKey="name" stroke="#565A75" fontSize={10} fontFamily="IBM Plex Mono" interval={0} angle={-20} textAnchor="end" height={70} />
              <YAxis stroke="#565A75" fontSize={11} fontFamily="IBM Plex Mono" domain={[0, 1]} />
              <Tooltip
                contentStyle={{ background: "#131320", border: "1px solid #242438", borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="precision" fill="#9B8CFF" radius={[3, 3, 0, 0]} />
              <Bar dataKey="recall" fill="#5B9CFF" radius={[3, 3, 0, 0]} />
              <Bar dataKey="f1" fill="#FFB454" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-sm font-semibold">Generate fidelity</div>
            <p className="text-xs text-muted mt-0.5">
              How statistically indistinguishable synthetic attacks are from a reference draw of the same
              pattern (discriminator-AUC based, see README for methodology).
            </p>
          </div>
          <button
            onClick={() => runAllFidelity()}
            disabled={loadingFidelity}
            className="flex items-center gap-2 text-xs font-mono font-semibold text-accent border border-accent/40 px-3 py-1.5 rounded-lg hover:bg-accent/10 disabled:opacity-50 shrink-0"
          >
            {loadingFidelity && <Loader2 size={13} className="animate-spin" />}
            {loadingFidelity ? "Running…" : "Re-run fidelity check"}
          </button>
        </div>

        <div className="space-y-2">
          {taxonomy.map((t) => {
            const r = fidelityResults[t.attack_id];
            return (
              <div key={t.attack_id} className="bg-panel border border-border rounded-lg p-3 flex items-center justify-between">
                <span className="text-sm">{t.display_name}</span>
                {r ? (
                  <div className="flex items-center gap-3 text-xs font-mono">
                    <span className="text-faint">{r.interpretation}</span>
                    <span className="text-faint" title="raw discriminator AUC -- 0.5 = indistinguishable, 1.0 = trivially distinguishable">
                      AUC {r.discriminator_auc}
                    </span>
                    <span className="text-accent font-semibold" title="fidelity_score = 1 - 2*|AUC - 0.5|">
                      fidelity {r.fidelity_score}
                    </span>
                  </div>
                ) : (
                  <span className="text-xs font-mono text-faint">—</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Robustness: threshold tuning + live adversarial check */}
      <RobustnessSection taxonomy={taxonomy} />
    </div>
  );
}

function RobustnessSection({ taxonomy }) {
  const thresholdable = taxonomy.filter(
    (t) => t.attack_id === "account_takeover" || t.specialist_tier === "auto"
  );
  const [selected, setSelected] = useState(null);
  const [curve, setCurve] = useState(null);
  const [loadingCurve, setLoadingCurve] = useState(false);
  const [evolveResult, setEvolveResult] = useState(null);
  const [evolving, setEvolving] = useState(false);
  const [regimes, setRegimes] = useState(null);
  const [loadingRegimes, setLoadingRegimes] = useState(false);

  useEffect(() => {
    if (thresholdable.length > 0 && !selected) setSelected(thresholdable[0].attack_id);
  }, [thresholdable]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selected) return;
    setLoadingCurve(true);
    setEvolveResult(null);
    setRegimes(null);
    api.thresholdCurve(selected).then(setCurve).catch(() => setCurve(null)).finally(() => setLoadingCurve(false));
  }, [selected]);

  const runEvaluationRegimes = async () => {
    if (!selected) return;
    setLoadingRegimes(true);
    try {
      setRegimes(await api.evaluationRegimes(selected));
    } catch {
      setRegimes(null);
    } finally {
      setLoadingRegimes(false);
    }
  };

  const runAdversarial = async () => {
    if (!selected) return;
    setEvolving(true);
    try {
      setEvolveResult(await api.evolveAttack(selected));
    } catch {
      setEvolveResult(null);
    } finally {
      setEvolving(false);
    }
  };

  if (thresholdable.length === 0) return null;

  return (
    <div>
      <div>
        <div className="text-sm font-semibold">Robustness: threshold tuning &amp; adversarial stress test</div>
        <p className="text-xs text-muted mt-0.5">
          A single reported false-positive rate is one operating point, not the whole story. This shows
          the recall/FPR tradeoff at other thresholds, plus a live red-team-vs-blue-team check —
          in-distribution metrics above, out-of-distribution evidence here.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        {thresholdable.map((t) => (
          <button
            key={t.attack_id}
            onClick={() => setSelected(t.attack_id)}
            className={`text-xs font-mono px-2.5 py-1 rounded-lg border transition-colors ${
              selected === t.attack_id
                ? "border-accent bg-accent/10 text-accent"
                : "border-border text-faint hover:text-muted"
            }`}
          >
            {t.display_name}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-faint uppercase tracking-wider mb-3">
            <Sliders size={12} /> Threshold tradeoff
          </div>
          {loadingCurve && <div className="text-xs text-faint font-mono">computing…</div>}
          {!loadingCurve && curve && (
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-faint text-[10px] uppercase">
                  <th className="text-left pb-1.5">Threshold</th>
                  <th className="text-right pb-1.5">Recall</th>
                  <th className="text-right pb-1.5">FPR</th>
                  <th className="text-right pb-1.5">Precision</th>
                </tr>
              </thead>
              <tbody>
                {curve.curve.map((row) => (
                  <tr
                    key={row.threshold}
                    className={row.threshold === 0.5 ? "text-ink bg-panel2/60" : "text-muted"}
                  >
                    <td className="py-1">{row.threshold}{row.threshold === 0.5 && " (default)"}</td>
                    <td className="text-right py-1">{(row.recall * 100).toFixed(1)}%</td>
                    <td className="text-right py-1 text-danger">{(row.false_positive_rate * 100).toFixed(2)}%</td>
                    <td className="text-right py-1">{(row.precision * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!loadingCurve && !curve && (
            <div className="text-xs text-faint">
              No single probability model for this specialist (hybrid Groq/rule-based) — threshold
              sweeps aren't meaningful here.
            </div>
          )}
        </div>

        <div className="bg-panel border border-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-faint uppercase tracking-wider">
              <Swords size={12} /> Live adversarial check
            </div>
            <button
              onClick={runAdversarial}
              disabled={evolving}
              className="text-[10px] font-mono text-warn border border-warn/40 px-2 py-1 rounded hover:bg-warn/10 disabled:opacity-50"
            >
              {evolving ? <Loader2 size={11} className="animate-spin" /> : "Run now"}
            </button>
          </div>
          {!evolveResult && <div className="text-xs text-faint">Not run yet this session.</div>}
          {evolveResult && !evolveResult.round_2 && (
            <div className="text-xs text-muted">{evolveResult.mutation?.reason}</div>
          )}
          {evolveResult?.round_2 && (
            <div className="grid grid-cols-2 gap-2 text-center">
              <div>
                <div className="text-[9px] font-mono text-faint uppercase">Original</div>
                <div className="text-lg font-mono font-bold" style={{ color: tierColor(evolveResult.round_1.final_risk_score) }}>
                  {evolveResult.round_1.final_risk_score.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono text-faint uppercase">Mutated</div>
                <div className="text-lg font-mono font-bold" style={{ color: tierColor(evolveResult.round_2.final_risk_score) }}>
                  {evolveResult.round_2.final_risk_score.toFixed(2)}
                </div>
              </div>
              <div className={`col-span-2 text-[10px] font-mono font-semibold ${evolveResult.mutation.evaded ? "text-danger" : "text-safe"}`}>
                {evolveResult.mutation.evaded ? "⚠ evasion successful" : "✓ still detected"}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* IID vs cross-generator vs adversarial-OOD -- the evidence table */}
      <div className="bg-panel border border-border rounded-xl p-4 mt-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-[10px] font-mono text-faint uppercase tracking-wider">
              Evaluation regimes — IID vs cross-generator vs adversarial-OOD
            </div>
            <p className="text-[10px] text-muted mt-1 max-w-lg">
              One headline F1 doesn't prove generalization. IID is the easiest test (same distribution
              as training) — expect it to look best. The other two are what actually matter.
            </p>
          </div>
          <button
            onClick={runEvaluationRegimes}
            disabled={loadingRegimes || !selected}
            className="text-[10px] font-mono text-accent border border-accent/40 px-2 py-1 rounded hover:bg-accent/10 disabled:opacity-50 shrink-0"
          >
            {loadingRegimes ? <Loader2 size={11} className="animate-spin" /> : "Run evaluation"}
          </button>
        </div>

        {!regimes && !loadingRegimes && (
          <div className="text-xs text-faint font-mono">Not run yet for this specialist.</div>
        )}

        {regimes && (
          <div className="space-y-3">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-faint text-[10px] uppercase">
                  <th className="text-left pb-1.5">Regime</th>
                  <th className="text-right pb-1.5">Precision</th>
                  <th className="text-right pb-1.5">Recall</th>
                  <th className="text-right pb-1.5">F1</th>
                  <th className="text-right pb-1.5">FPR</th>
                </tr>
              </thead>
              <tbody>
                <tr className="text-muted">
                  <td className="py-1">IID</td>
                  <td className="text-right py-1">{(regimes.iid.precision * 100).toFixed(1)}%</td>
                  <td className="text-right py-1">{(regimes.iid.recall * 100).toFixed(1)}%</td>
                  <td className="text-right py-1 text-ink">{(regimes.iid.f1 * 100).toFixed(1)}%</td>
                  <td className="text-right py-1 text-danger">{(regimes.iid.false_positive_rate * 100).toFixed(2)}%</td>
                </tr>
                <tr className="text-muted border-t border-border/40">
                  <td className="py-1">Cross-generator</td>
                  <td className="text-right py-1">{(regimes.cross_generator.precision * 100).toFixed(1)}%</td>
                  <td className="text-right py-1">{(regimes.cross_generator.recall * 100).toFixed(1)}%</td>
                  <td className="text-right py-1 text-ink">{(regimes.cross_generator.f1 * 100).toFixed(1)}%</td>
                  <td className="text-right py-1 text-danger">{(regimes.cross_generator.false_positive_rate * 100).toFixed(2)}%</td>
                </tr>
                <tr className="text-muted border-t border-border/40">
                  <td className="py-1">Adversarial-OOD</td>
                  <td colSpan={3} className="text-right py-1">
                    {regimes.adversarial_ood.blue_win_rate !== null
                      ? `${(regimes.adversarial_ood.blue_win_rate * 100).toFixed(1)}% blue win rate`
                      : "not evaluable this run"}
                  </td>
                  <td className="text-right py-1 text-faint">
                    {regimes.adversarial_ood.rounds_scored} rounds
                  </td>
                </tr>
              </tbody>
            </table>
            <div className="text-[10px] text-faint leading-relaxed">{regimes.cross_generator.data_source}</div>
            <div className="text-[10px] text-muted leading-relaxed border-t border-border pt-2">{regimes.interpretation}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ name, m, accentClass }) {
  const fpr = m.false_positive_rate_on_legit;
  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className={`text-sm font-semibold capitalize mb-3 ${accentClass}`}>{name.replace(/_/g, " ")}</div>
      <div className="grid grid-cols-4 gap-2">
        {Object.entries(m)
          .filter(([k]) => k !== "trained_on" && k !== "false_positive_rate_on_legit")
          .map(([k, v]) => (
            <div key={k} className="bg-panel2 rounded-lg p-2.5 text-center">
              <div className={`text-lg font-mono font-semibold ${accentClass}`}>{v}</div>
              <div className="text-[9px] text-faint uppercase tracking-wider mt-0.5">{k}</div>
            </div>
          ))}
      </div>
      {fpr !== undefined && (
        <div className="mt-3 flex items-center justify-between bg-danger/5 border border-danger/20 rounded-lg px-3 py-2">
          <span className="text-[10px] font-mono text-faint uppercase tracking-wider">
            False positive rate on legitimate payments
          </span>
          <span className="text-sm font-mono font-semibold text-danger">{(fpr * 100).toFixed(2)}%</span>
        </div>
      )}
      {m.trained_on && <div className="text-[10px] font-mono text-faint mt-2">{m.trained_on}</div>}
    </div>
  );
}
