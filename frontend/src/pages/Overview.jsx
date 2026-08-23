import { ArrowRight, Zap, Key, PlayCircle, Swords } from "lucide-react";
import PipelineDiagram from "../components/PipelineDiagram";
import WhyThisMatters from "../components/WhyThisMatters";

export default function Overview({ onNavigate }) {
  return (
    <div className="max-w-4xl mx-auto space-y-10">
      <div>
        <h2 className="font-display text-2xl font-semibold">How Orion works</h2>
        <p className="text-sm text-muted mt-2 leading-relaxed max-w-2xl">
          A closed-loop red-team/blue-team system for payment fraud. It doesn't just detect fraud —
          it discovers and synthesizes plausible emerging fraud patterns from threat intelligence and
          observed anomalous behavior, generates statistically calibrated synthetic attacks for
          controlled stress testing, and trains detectors against those attacks. When something slips
          past every specialist, the system notices, names the new pattern, and trains a detector for
          it — automatically. Its red team then mutates those patterns to stress-test the defense.
        </p>
      </div>

      {/* The real business case, cited */}
      <WhyThisMatters />

      {/* Open-world framing, front and center */}
      <div className="flex items-center gap-4 bg-accent/5 border border-accent/25 rounded-xl px-5 py-4">
        <div className="text-2xl font-mono font-bold text-accent shrink-0">7 → 8 → 9 → 10+</div>
        <div className="text-xs text-muted leading-relaxed">
          <span className="text-ink font-medium">Open-world discovery loop.</span> Orion isn't limited to a
          fixed taxonomy — the defense expands automatically as the threat landscape changes. See it
          happen live in Simulate.
        </div>
      </div>

      {/* The pipeline, visualized */}
      <PipelineDiagram />

      {/* Two-tier defense explainer */}
      <div className="bg-panel border border-border rounded-xl p-5">
        <div className="text-sm font-semibold mb-3">Two tiers of specialist, both fully working</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="border border-safe/30 rounded-lg p-3">
            <div className="font-mono text-safe font-semibold mb-1.5 uppercase tracking-wide text-[10px]">Deep (4)</div>
            <p className="text-muted leading-relaxed">
              Hand-engineered logic for the 4 highest-volume fraud types: voice-clone vishing,
              fake app/QR substitution, account takeover, synthetic identity/KYC. Each uses
              detection logic specific to that attack — a Groq semantic prompt, a deterministic
              registry check, a trained classifier on curated features.
            </p>
          </div>
          <div className="border border-accent/30 rounded-lg p-3">
            <div className="font-mono text-accent font-semibold mb-1.5 uppercase tracking-wide text-[10px]">Auto (3 + growing)</div>
            <p className="text-muted leading-relaxed">
              Everything else, including any pattern the system discovers on its own. Gets a real
              trained classifier (LogisticRegression) built the moment its taxonomy entry exists —
              not a placeholder. See real precision/recall/F1/AUC for each in Agent Roster.
            </p>
          </div>
        </div>
      </div>

      {/* Groq status note */}
      <div className="flex items-start gap-3 bg-panel2 border border-border rounded-xl p-4">
        <Key size={16} className="text-warn mt-0.5 shrink-0" />
        <div className="text-xs text-muted leading-relaxed">
          <span className="text-ink font-medium">No Groq API key needed to try this.</span> Every
          Groq-backed call has a deterministic offline fallback, so routing, detection, and the
          closed loop all work without a key — you'll just see generic fallback text instead of
          LLM-generated content (e.g. a generic pattern name instead of one written from your
          actual case summaries). Add a free key at{" "}
          <a href="https://console.groq.com" target="_blank" rel="noreferrer" className="text-accent hover:underline">
            console.groq.com
          </a>{" "}
          and drop it in <code className="font-mono text-faint">backend/.env</code> for the full experience.
        </div>
      </div>

      {/* How to test it, step by step */}
      <div>
        <div className="text-sm font-semibold mb-3 flex items-center gap-2">
          <PlayCircle size={16} className="text-accent" />
          Try it in under a minute
        </div>
        <ol className="space-y-2.5">
          <Step n={1} onClick={() => onNavigate("simulate")}>
            Go to <b className="text-ink">Simulate</b>, pick any attack card, click{" "}
            <span className="font-mono text-accent">Generate &amp; run detection</span>. You'll see
            a synthetic attack get created and scored in real time, with the reasons behind the score.
          </Step>
          <Step n={2} onClick={() => onNavigate("roster")}>
            Check <b className="text-ink">Agent Roster</b> — every specialist listed there is live
            and working, with real metrics for the auto tier.
          </Step>
          <Step n={3} onClick={() => onNavigate("feed")}>
            Open <b className="text-ink">Live Feed</b> to see every case processed so far — click
            any row for the full routing/specialist/generalist breakdown.
          </Step>
          <Step n={4} icon={Zap} onClick={() => onNavigate("simulate")}>
            Back in Simulate, click{" "}
            <span className="font-mono text-accent">Trigger pattern discovery</span> — this is the
            closed loop: it invents a new fraud pattern, names it, and trains a real detector for
            it, live, in front of you.
          </Step>
          <Step n={5} icon={Swords} onClick={() => onNavigate("simulate")}>
            Select any pattern in Simulate and click{" "}
            <span className="font-mono text-warn">Evolve this attack</span> — the red team
            mutates the case to try to evade the blue team's own detector, live, and shows you
            whether it worked.
          </Step>
          <Step n={6} icon={Swords} onClick={() => onNavigate("arena")}>
            Head to <b className="text-ink">Arena</b> for the persistent version — a running
            scoreboard, a leaderboard of which specialists are toughest to evade, and a{" "}
            <span className="font-mono text-warn">FIGHT!</span> button for multi-round matches.
          </Step>
        </ol>
      </div>
    </div>
  );
}

function Step({ n, children, onClick, icon: Icon }) {
  return (
    <li
      onClick={onClick}
      className="flex items-start gap-3 bg-panel border border-border rounded-lg p-3.5 cursor-pointer hover:border-accent/40 transition-colors group"
    >
      <div className="w-6 h-6 rounded-full bg-accent/15 text-accent text-xs font-mono font-semibold flex items-center justify-center shrink-0">
        {n}
      </div>
      <p className="text-xs text-muted leading-relaxed flex-1">{children}</p>
      <ArrowRight size={14} className="text-faint group-hover:text-accent transition-colors shrink-0 mt-0.5" />
    </li>
  );
}
