import { useEffect, useState } from "react";
import { ShieldCheck, Loader2, ExternalLink, TrendingUp, AlertCircle, Download } from "lucide-react";
import api from "../api";

function buildMarkdownReport(report) {
  const lines = [];
  lines.push(`# ${report.title}`);
  lines.push("");
  lines.push(`**Report ID:** ${report.report_id}  `);
  lines.push(`**Generated:** ${new Date(report.generated_at).toLocaleString()}`);
  lines.push("");
  lines.push(`> ${report.disclaimer}`);
  lines.push("");
  lines.push("## Regulatory basis");
  lines.push(`- **Framework:** ${report.regulatory_basis.framework} (${report.regulatory_basis.published})`);
  lines.push(`- **Status:** ${report.regulatory_basis.status}`);
  lines.push(`- **Recommendation ${report.regulatory_basis.primary_recommendation.number} — ${report.regulatory_basis.primary_recommendation.title}** (${report.regulatory_basis.primary_recommendation.pillar} pillar): "${report.regulatory_basis.primary_recommendation.text}"`);
  lines.push(`- **Related — Recommendation ${report.regulatory_basis.related_recommendation.number} (${report.regulatory_basis.related_recommendation.title}):** ${report.regulatory_basis.related_recommendation.text}`);
  lines.push(`- ${report.regulatory_basis.orion_claim}`);
  lines.push("");
  lines.push("## Summary");
  lines.push(`- Attack families tested: ${report.summary.attack_families_tested}`);
  lines.push(`- Attack families excluded: ${report.summary.attack_families_excluded.join(", ") || "none"}`);
  lines.push(`- Rounds conducted: ${report.summary.rounds_conducted}`);
  lines.push(`- Overall blue win rate: ${report.summary.overall_blue_win_rate !== null ? (report.summary.overall_blue_win_rate * 100).toFixed(1) + "%" : "n/a"}`);
  lines.push(`- Newly discovered patterns this session: ${report.summary.newly_discovered_patterns_this_session}`);
  lines.push("");
  lines.push("## Per-specialist detail");
  lines.push("| Specialist | Tier | Model version | Blue win rate | FPR on legit | Fidelity |");
  lines.push("|---|---|---|---|---|---|");
  for (const s of report.per_specialist) {
    lines.push(`| ${s.display_name} | ${s.tier} | ${s.model_version} | ${s.blue_win_rate !== null ? (s.blue_win_rate * 100).toFixed(1) + "%" : "—"} | ${s.false_positive_rate_on_legit !== undefined && s.false_positive_rate_on_legit !== null ? (s.false_positive_rate_on_legit * 100).toFixed(2) + "%" : "—"} | ${s.fidelity_score ?? "—"} |`);
  }
  lines.push("");
  if (report.worst_performing_specialists.length > 0) {
    lines.push("## Worst-performing specialists (lowest blue win rate)");
    for (const w of report.worst_performing_specialists) {
      lines.push(`- ${w.display_name}: ${(w.blue_win_rate * 100).toFixed(1)}% (${w.blue_wins}W-${w.red_wins}L)`);
    }
    lines.push("");
  }
  if (report.newly_discovered_patterns.length > 0) {
    lines.push("## Newly discovered patterns this session");
    for (const d of report.newly_discovered_patterns) {
      lines.push(`- **${d.display_name}** — discovered ${d.created_at ? new Date(d.created_at).toLocaleString() : "—"}, grounded in ${d.research_source_count} live source(s)`);
    }
    lines.push("");
  }
  lines.push("## Methodology");
  lines.push(report.methodology);
  return lines.join("\n");
}

function downloadFile(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function AssuranceSection() {
  const [history, setHistory] = useState([]);
  const [latest, setLatest] = useState(null);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [exporting, setExporting] = useState(false);

  const load = () => {
    api.auditHistory().then((r) => setHistory(r.history)).catch(() => {});
    api.latestAudit().then(setLatest).catch(() => setLatest(null));
  };

  useEffect(() => { load(); }, []);

  const runAudit = async () => {
    setRunning(true);
    try {
      const result = await api.runAudit(3);
      setLatest(result);
      load();
    } catch {
      /* surfaced via absence of a new result */
    } finally {
      setRunning(false);
    }
  };

  const exportReport = async () => {
    setExporting(true);
    try {
      const report = await api.fullAssuranceReport(3);
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      downloadFile(`orion-assurance-report-${stamp}.md`, buildMarkdownReport(report), "text/markdown");
      downloadFile(`orion-assurance-report-${stamp}.json`, JSON.stringify(report, null, 2), "application/json");
      load();
    } catch {
      /* export failure is non-critical; dashboard state is unaffected */
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold flex items-center gap-1.5">
            <ShieldCheck size={16} className="text-info" />
            Assure — periodic red-teaming audit
          </div>
          <p className="text-xs text-muted mt-1 leading-relaxed max-w-xl">
            Operationalizes{" "}
            <span className="text-ink">Recommendation 20 ("Red Teaming")</span> from RBI's FREE-AI
            Committee Report (13 Aug 2025, Protection pillar): structured, trigger-based red-teaming
            across the AI lifecycle. This is a committee recommendation, not a binding mandate — Orion
            generates the evidence a regulated entity's own governance process would use, it doesn't
            claim to make anyone compliant.
          </p>
        </div>
        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={runAudit}
            disabled={running}
            className="flex items-center gap-2 text-xs font-mono font-semibold text-info border border-info/40 px-3 py-2 rounded-lg hover:bg-info/10 disabled:opacity-50"
          >
            {running ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
            Run audit
          </button>
          <button
            onClick={exportReport}
            disabled={exporting}
            className="flex items-center gap-2 text-xs font-mono font-semibold text-muted border border-border px-3 py-2 rounded-lg hover:bg-panel2 disabled:opacity-50"
          >
            {exporting ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
            Export report
          </button>
        </div>
      </div>

      {!latest && !running && (
        <div className="text-xs text-faint font-mono py-3">No audit run yet this session.</div>
      )}

      {latest && (
        <div className="bg-panel border border-border rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-xs font-mono text-faint">
              audit <span className="text-ink">{latest.audit_id}</span> ·{" "}
              {new Date(latest.conducted_at).toLocaleString()}
            </div>
            <div className="text-right">
              <div className="text-2xl font-mono font-bold text-info">
                {latest.overall_blue_win_rate !== null ? `${(latest.overall_blue_win_rate * 100).toFixed(0)}%` : "—"}
              </div>
              <div className="text-[9px] font-mono text-faint uppercase">overall blue win rate</div>
            </div>
          </div>

          <div className="text-[10px] font-mono text-faint">
            {latest.total_rounds_scored} scored rounds across {latest.specialists_audited} specialists
            {latest.specialists_excluded.length > 0 && (
              <span> · excluded: {latest.specialists_excluded.join(", ")} (deterministic, no meaningful mutation)</span>
            )}
          </div>

          {/* Legend -- explains why win rates vary so widely between specialists */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] font-mono text-muted bg-panel2/60 rounded-lg px-3 py-2">
            <span className="flex items-center gap-1.5"><span className="text-safe font-semibold">100%</span> = detector held every mutation attempt</span>
            <span className="flex items-center gap-1.5"><span className="text-danger font-semibold">0%</span> = red team evaded every attempt — a real found weakness</span>
            <span className="flex items-center gap-1.5"><AlertCircle size={10} className="text-muted" /> no scored rounds = round 1 was never caught, so there was nothing to evade (not a battle loss)</span>
          </div>

          <div className="space-y-1">
            {latest.per_specialist.map((s) => (
              <div key={s.attack_id} className="flex items-center justify-between text-xs bg-panel2 rounded-lg px-3 py-2">
                <span className="truncate">{s.display_name}</span>
                <span className="font-mono text-muted">
                  {s.blue_win_rate !== null ? (
                    <span className={s.blue_win_rate >= 0.5 ? "text-safe" : "text-danger"} title={s.blue_win_rate >= 0.5 ? "Detector held up against mutation attempts" : "Red team's mutations evaded detection more often than not -- a real, demonstrated weakness"}>
                      {(s.blue_win_rate * 100).toFixed(0)}%
                    </span>
                  ) : (
                    <span
                      className="flex items-center gap-1 text-muted"
                      title="Round 1 (the original, unmutated attack) was never caught in these attempts, so there was nothing for the red team to evade. Not a loss for either side -- run more rounds or check that this attack type is actually detectable at all."
                    >
                      <AlertCircle size={10} /> no scored rounds
                    </span>
                  )}
                  <span className="text-faint ml-2">({s.blue_wins}W-{s.red_wins}L)</span>
                </span>
              </div>
            ))}
          </div>

          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-[10px] font-mono text-info hover:underline"
          >
            {expanded ? "hide" : "show"} regulatory basis + methodology
          </button>

          {expanded && (
            <div className="text-[10px] font-mono text-muted bg-panel2 rounded-lg p-3 space-y-2 leading-relaxed">
              <div>
                <span className="text-ink">Rec {latest.regulatory_basis.primary_recommendation.number} — {latest.regulatory_basis.primary_recommendation.title}</span>{" "}
                ({latest.regulatory_basis.primary_recommendation.pillar} pillar): "{latest.regulatory_basis.primary_recommendation.text}"
              </div>
              <div>{latest.regulatory_basis.orion_claim}</div>
              <div className="text-warn">{latest.regulatory_basis.status}</div>
              <div className="pt-1 border-t border-border/60">{latest.methodology}</div>
            </div>
          )}
        </div>
      )}

      {history.length > 1 && (
        <div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-faint uppercase tracking-wider mb-2">
            <TrendingUp size={11} /> Trend across {history.length} audits this session
          </div>
          <div className="flex items-end gap-1.5 h-16">
            {history.map((h) => (
              <div key={h.audit_id} className="flex-1 flex flex-col items-center justify-end gap-1">
                <div
                  className="w-full bg-info/40 rounded-t"
                  style={{ height: `${(h.overall_blue_win_rate || 0) * 100}%`, minHeight: 2 }}
                  title={`${h.audit_id}: ${((h.overall_blue_win_rate || 0) * 100).toFixed(0)}%`}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-[10px] text-muted leading-relaxed border-t border-border pt-3">
        This report is a technical red-team evidence artifact. It does not constitute an RBI
        compliance certification or legal opinion.
      </div>
    </div>
  );
}
