import { useEffect, useState } from "react";
import { ShieldCheck, Shield, Radar, Sparkles, Infinity as InfinityIcon } from "lucide-react";
import api from "../api";
import ErrorState from "../components/ErrorState";

export default function AgentRoster() {
  const [agents, setAgents] = useState(null);
  const [error, setError] = useState(null);

  const load = () => {
    api.agents()
      .then((r) => { setAgents(r); setError(null); })
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 6000);
    return () => clearInterval(id);
  }, []);

  if (error && !agents) return <ErrorState message={error} onRetry={load} />;
  if (!agents) return <div className="text-faint text-sm font-mono">loading roster…</div>;

  const deep = agents.specialists.filter((a) => a.tier === "deep");
  const auto = agents.specialists.filter((a) => a.tier === "auto");
  const discovered = agents.specialists.filter((a) => a.seed_or_discovered === "discovered");

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h2 className="font-display text-xl font-semibold">Agent roster</h2>
        <p className="text-sm text-muted mt-1">
          {deep.length} deep specialists · {auto.length} auto-trained specialists · 1 generalist always
          running as the safety net{discovered.length > 0 && ` · ${discovered.length} discovered via the closed loop`}
        </p>
        <p className="text-xs text-faint mt-1">
          Every entry here has a real working detector — the two tiers differ in depth of engineering, not in whether they function.
        </p>
      </div>

      <div className="flex items-center gap-3 bg-accent/5 border border-accent/25 rounded-xl px-4 py-3">
        <InfinityIcon size={18} className="text-accent shrink-0" />
        <div className="text-xs text-muted leading-relaxed">
          <span className="text-accent font-semibold">Open-world discovery loop.</span> Orion isn't limited to
          the {agents.specialists.length} seeded attack classes — the roster grows in real time as the
          closed loop discovers new patterns. Each promotion trains a real classifier immediately, no
          manual step. Try it from the Simulate tab.
        </div>
      </div>

      {/* Generalist - persistent card */}
      <div className="bg-panel border border-info/30 rounded-xl p-4 flex items-center gap-4">
        <div className="w-11 h-11 rounded-lg bg-info/15 flex items-center justify-center shrink-0">
          <Radar size={20} className="text-info" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold">{agents.generalist.display_name}</div>
          <div className="text-xs text-muted mt-0.5">{agents.generalist.role} · always on, every case</div>
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-info/15 text-info uppercase tracking-wider">
          persistent
        </span>
      </div>

      <div>
        <SectionHeading>Deep specialists — hand-engineered detection logic</SectionHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
          {deep.map((a) => (
            <AgentCard key={a.attack_id} agent={a} tier="deep" />
          ))}
        </div>
      </div>

      <div>
        <SectionHeading>Auto-trained specialists — real classifier, trained on creation</SectionHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
          {auto.map((a) => (
            <AgentCard key={a.attack_id} agent={a} tier="auto" />
          ))}
          {auto.length === 0 && (
            <div className="text-xs text-faint font-mono col-span-2 py-4">No auto-tier entries.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function AgentCard({ agent, tier }) {
  const isDeep = tier === "deep";
  const isShadow = agent.lifecycle_stage === "shadow";
  return (
    <div
      className={`rounded-xl p-4 flex items-start gap-3 bg-panel border ${
        isShadow ? "border-warn/40 border-dashed" : isDeep ? "border-safe/30" : "border-accent/25"
      }`}
    >
      <div
        className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
          isShadow ? "bg-warn/15" : isDeep ? "bg-safe/15" : "bg-accent/15"
        }`}
      >
        {isDeep ? <ShieldCheck size={17} className="text-safe" /> : <Shield size={17} className={isShadow ? "text-warn" : "text-accent"} />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium truncate">{agent.display_name}</span>
          {agent.seed_or_discovered === "discovered" && (
            <span className="text-[9px] font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded border border-accent/30 shrink-0 flex items-center gap-1">
              <Sparkles size={9} /> AUTO-DISCOVERED
            </span>
          )}
          {isShadow && (
            <span
              className="text-[9px] font-mono text-warn bg-warn/10 px-1.5 py-0.5 rounded border border-warn/30 shrink-0"
              title="Trained and testable, but not yet routing live traffic -- failed the governance gate. See reasons below."
            >
              SHADOW — NOT LIVE
            </span>
          )}
        </div>
        <div className="text-xs text-faint font-mono mt-1">{agent.channel}</div>
        {isShadow && agent.gate_result?.reasons_failed?.length > 0 && (
          <div className="mt-1.5 space-y-0.5">
            {agent.gate_result.reasons_failed.map((r, i) => (
              <div key={i} className="text-[10px] text-warn leading-snug">⚠ {r}</div>
            ))}
          </div>
        )}
        {agent.auto_metrics && (
          <div className="flex gap-3 mt-2 text-[10px] font-mono text-faint">
            <span>P {agent.auto_metrics.precision}</span>
            <span>R {agent.auto_metrics.recall}</span>
            <span>F1 {agent.auto_metrics.f1}</span>
          </div>
        )}
        {agent.last_researched_at && (
          <div className="text-[10px] font-mono text-info mt-1">
            {agent.research_source_count} source(s) · researched {new Date(agent.last_researched_at).toLocaleDateString()}
          </div>
        )}
      </div>
      <span
        className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider shrink-0 ${
          isDeep ? "bg-safe/15 text-safe" : "bg-accent/15 text-accent"
        }`}
      >
        {tier}
      </span>
    </div>
  );
}

function SectionHeading({ children }) {
  return <div className="text-xs font-mono text-faint uppercase tracking-wider">{children}</div>;
}
