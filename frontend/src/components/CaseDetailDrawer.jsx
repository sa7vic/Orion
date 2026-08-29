import { X } from "lucide-react";
import RiskGauge, { tierColor } from "../components/RiskGauge";

const POLICY_COLOR = {
  ALLOW: "text-safe bg-safe/10 border-safe/30",
  MONITOR: "text-info bg-info/10 border-info/30",
  STEP_UP: "text-warn bg-warn/10 border-warn/30",
  BLOCK: "text-danger bg-danger/10 border-danger/30",
};

export default function CaseDetailDrawer({ caseData, onClose, displayName = (id) => id }) {
  if (!caseData) return null;
  const { routing, specialist_result, generalist_result, final_reasons, triggered_promotion } = caseData;

  return (
    <div className="fixed inset-0 z-30 flex justify-end">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]" onClick={onClose} />
      <div className="relative w-full max-w-md h-full bg-panel border-l border-border shadow-2xl overflow-y-auto animate-[slideIn_0.2s_ease]">
        <div className="sticky top-0 bg-panel/95 backdrop-blur-sm border-b border-border px-5 py-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-mono text-faint">CASE {caseData.case_id}</div>
            <div className="text-sm font-medium mt-0.5">{caseData.channel || "unknown channel"}</div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink p-1">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="flex items-center gap-4 bg-panel2 rounded-xl p-4 border border-border">
            <RiskGauge score={caseData.final_risk_score} size={80} />
            <div className="flex-1">
              <div className="text-[10px] font-mono text-faint uppercase tracking-wider">Final verdict</div>
              <div className="text-lg font-display font-semibold" style={{ color: tierColor(caseData.final_risk_score) }}>
                {caseData.risk_tier?.toUpperCase()} RISK
              </div>
              <div className="text-xs text-muted mt-1 font-mono">{caseData.timestamp?.slice(0, 19).replace("T", " ")}</div>
            </div>
            {caseData.policy && (
              <span className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-lg border shrink-0 ${POLICY_COLOR[caseData.policy.action] || ""}`}>
                {caseData.policy.action.replace("_", "-")}
              </span>
            )}
          </div>

          {caseData.policy && (
            <div className="text-xs text-muted bg-panel2 border border-border rounded-lg p-3 -mt-2">
              {caseData.policy.rationale}
            </div>
          )}

          {triggered_promotion && (
            <div className="bg-accent/10 border border-accent/30 rounded-xl p-3.5">
              <div className="text-xs font-semibold text-accent mb-1">◆ Closed loop triggered</div>
              <div className="text-xs text-muted leading-relaxed">
                This case's pattern crossed the promotion threshold. A new specialist{" "}
                <span className="font-mono text-ink">{triggered_promotion.display_name}</span> was just created.
              </div>
            </div>
          )}

          <div>
            <SectionLabel>Case summary</SectionLabel>
            <div className="text-xs font-mono text-muted bg-panel2 rounded-lg p-3 border border-border leading-relaxed break-words">
              {caseData.summary}
            </div>
          </div>

          <div>
            <SectionLabel>Router decision</SectionLabel>
            <div className="bg-panel2 rounded-lg p-3 border border-border space-y-1.5 text-xs">
              <Row label="Routed to" value={routing?.attack_id ? displayName(routing.attack_id) : "generalist (low confidence)"} />
              <Row label="Confidence" value={routing?.confidence?.toFixed(3)} />
              {routing?.scores && (
                <div className="pt-1.5 border-t border-border/60 mt-1.5">
                  {Object.entries(routing.scores).map(([id, s]) => (
                    <div key={id} className="flex justify-between font-mono text-[11px] text-faint py-0.5">
                      <span>{displayName(id)}</span>
                      <span>{s.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {specialist_result && (
            <div>
              <SectionLabel>Specialist: {specialist_result.specialist}</SectionLabel>
              <ResultBlock result={specialist_result} />
            </div>
          )}

          <div>
            <SectionLabel>Generalist (always-on)</SectionLabel>
            <ResultBlock result={generalist_result} />
          </div>

          <div>
            <SectionLabel>All reasons (merged)</SectionLabel>
            <ul className="space-y-1.5">
              {final_reasons?.map((r, i) => (
                <li key={i} className="text-xs text-muted flex gap-2">
                  <span className="text-accent mt-0.5">›</span>
                  {r}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultBlock({ result }) {
  return (
    <div className="bg-panel2 rounded-lg p-3 border border-border space-y-1.5 text-xs">
      <Row label="Risk score" value={result.risk_score?.toFixed(3)} />
      {result.signal_breakdown &&
        Object.entries(result.signal_breakdown).map(([k, v]) => (
          <Row
            key={k}
            label={k.replace(/_/g, " ")}
            value={
              Array.isArray(v)
                ? v.join(", ")
                : v && typeof v === "object"
                ? Object.entries(v).map(([mk, mv]) => `${mk}: ${mv}`).join(" · ")
                : String(v)
            }
          />
        ))}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-faint capitalize">{label}</span>
      <span className="font-mono text-ink text-right">{value}</span>
    </div>
  );
}

function SectionLabel({ children }) {
  return <div className="text-[10px] font-mono text-faint uppercase tracking-wider mb-2">{children}</div>;
}
