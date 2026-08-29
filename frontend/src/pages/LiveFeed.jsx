import { useEffect, useState, useCallback } from "react";
import { RefreshCw, Inbox } from "lucide-react";
import api from "../api";
import RiskGauge, { tierColor } from "../components/RiskGauge";
import CaseDetailDrawer from "../components/CaseDetailDrawer";
import ErrorState from "../components/ErrorState";
import useTaxonomyMap from "../hooks/useTaxonomyMap";

const POLICY_COLOR = {
  ALLOW: "text-safe bg-safe/10 border-safe/30",
  MONITOR: "text-info bg-info/10 border-info/30",
  STEP_UP: "text-warn bg-warn/10 border-warn/30",
  BLOCK: "text-danger bg-danger/10 border-danger/30",
};

export default function LiveFeed() {
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { displayName } = useTaxonomyMap();

  const load = useCallback(() => {
    api.feed(50)
      .then((r) => { setCases(r.cases); setError(null); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    if (!autoRefresh) return;
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, [load, autoRefresh]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="font-display text-xl font-semibold">Live case feed</h2>
          <p className="text-sm text-muted mt-1">Every case processed by the router, specialists, and generalist — most recent first.</p>
        </div>
        <button
          onClick={() => setAutoRefresh((v) => !v)}
          className={`flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg border transition-colors ${
            autoRefresh ? "border-accent/40 text-accent bg-accent/5" : "border-border text-faint"
          }`}
        >
          <RefreshCw size={12} className={autoRefresh ? "animate-spin [animation-duration:2s]" : ""} />
          {autoRefresh ? "live" : "paused"}
        </button>
      </div>

      {error && cases.length === 0 && <ErrorState message={error} onRetry={load} />}

      {!error && loading && cases.length === 0 && (
        <div className="text-center py-20 text-faint text-sm font-mono">loading feed…</div>
      )}

      {!error && !loading && cases.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-faint gap-3">
          <Inbox size={32} strokeWidth={1.2} />
          <p className="text-sm">No cases yet. Head to Simulate to generate and detect an attack.</p>
        </div>
      )}

      <div className="space-y-2">
        {cases.map((c) => (
          <button
            key={c.case_id}
            onClick={() => setSelected(c)}
            className="w-full text-left bg-panel border border-border rounded-xl p-3.5 flex items-center gap-4 hover:border-accent/30 hover:bg-panel2 transition-colors group"
          >
            <RiskGauge score={c.final_risk_score} size={52} showLabel={false} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono font-semibold" style={{ color: tierColor(c.final_risk_score) }}>
                  {c.risk_tier?.toUpperCase()}
                </span>
                <span className="text-xs text-faint font-mono">·</span>
                <span className="text-xs font-mono text-muted">
                  {c.routing?.attack_id ? displayName(c.routing.attack_id) : "unrouted → generalist"}
                </span>
                {c.triggered_promotion && (
                  <span className="text-[10px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded border border-accent/30">
                    NEW AGENT SPAWNED
                  </span>
                )}
              </div>
              <p className="text-sm text-ink/90 truncate group-hover:text-ink">{c.summary}</p>
            </div>
            <div className="text-right shrink-0 flex flex-col items-end gap-1">
              {c.policy && (
                <span className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded border ${POLICY_COLOR[c.policy.action] || "text-faint border-border"}`}>
                  {c.policy.action.replace("_", "-")}
                </span>
              )}
              <div className="text-xs font-mono text-faint">{c.channel || "—"}</div>
              <div className="text-[10px] font-mono text-faint">{c.timestamp?.slice(11, 19)}</div>
            </div>
          </button>
        ))}
      </div>

      <CaseDetailDrawer caseData={selected} onClose={() => setSelected(null)} displayName={displayName} />
    </div>
  );
}
