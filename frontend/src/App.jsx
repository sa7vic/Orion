import { useState, useEffect, useCallback } from "react";
import { Compass, Activity, FlaskConical, Users, BarChart3, RotateCcw, Wifi, WifiOff, Swords } from "lucide-react";
import ShieldMark from "./components/ShieldMark";
import StarField from "./components/StarField";
import LiveFeed from "./pages/LiveFeed";
import Simulate from "./pages/Simulate";
import AgentRoster from "./pages/AgentRoster";
import Metrics from "./pages/Metrics";
import Overview from "./pages/Overview";
import Arena from "./pages/Arena";
import api from "./api";

const TABS = [
  { id: "overview", label: "How it works", icon: Compass },
  { id: "feed", label: "Live Feed", icon: Activity },
  { id: "simulate", label: "Simulate", icon: FlaskConical },
  { id: "arena", label: "Arena", icon: Swords },
  { id: "roster", label: "Agent Roster", icon: Users },
  { id: "metrics", label: "Metrics", icon: BarChart3 },
];

export default function App() {
  const [tab, setTab] = useState("overview");
  const [health, setHealth] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const pollHealth = useCallback(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "offline" }));
  }, []);

  useEffect(() => {
    pollHealth();
    const id = setInterval(pollHealth, 15000);
    return () => clearInterval(id);
  }, [pollHealth]);

  const handleReset = async () => {
    if (!confirm("Reset demo state? This clears the live feed and any promoted agents.")) return;
    await api.reset();
    setRefreshKey((k) => k + 1);
  };

  const online = health?.status === "ok";

  return (
    <div className="min-h-screen flex">
      <StarField />
      <aside className="w-56 shrink-0 border-r border-border bg-panel/90 backdrop-blur-sm flex flex-col">
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-border">
          <ShieldMark size={26} />
          <div>
            <div className="font-display font-semibold text-[15px] tracking-tight leading-none">ORION</div>
            <div className="text-[10px] text-faint font-mono tracking-widest mt-0.5">FRAUD DEFENSE LAB</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                tab === id
                  ? "bg-accent/10 text-accent border border-accent/30"
                  : "text-muted hover:text-ink hover:bg-panel2 border border-transparent"
              }`}
            >
              <Icon size={16} strokeWidth={2} />
              {label}
            </button>
          ))}
        </nav>

        <div className="px-3 pb-4">
          <button
            onClick={handleReset}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-faint hover:text-danger hover:bg-danger/5 transition-colors"
          >
            <RotateCcw size={14} />
            Reset demo
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-base/80 backdrop-blur-sm sticky top-0 z-10">
          <h1 className="font-display font-medium text-sm text-muted">
            {TABS.find((t) => t.id === tab)?.label}
          </h1>
          <div className="flex items-center gap-4 text-xs font-mono">
            {health && (
              <div className="flex items-center gap-1.5 text-faint">
                {health.groq_online ? <Wifi size={13} className="text-accent" /> : <WifiOff size={13} />}
                <span>{health.groq_online ? "groq: live" : "groq: offline-mock"}</span>
              </div>
            )}
            <div className={`flex items-center gap-1.5 ${online ? "text-safe" : "text-danger"}`}>
              <span className={`relative w-1.5 h-1.5 rounded-full ${online ? "bg-safe" : "bg-danger"}`}>
                {online && <span className="pulse-dot absolute inset-0 text-safe" />}
              </span>
              {online ? "api: online" : "api: unreachable"}
            </div>
          </div>
        </header>

        <main className="flex-1 p-6 overflow-y-auto">
          {tab === "overview" && <Overview onNavigate={setTab} />}
          {tab === "feed" && <LiveFeed key={`feed-${refreshKey}`} />}
          {tab === "simulate" && <Simulate key={`sim-${refreshKey}`} onCaseCreated={() => setTab("feed")} />}
          {tab === "arena" && <Arena key={`arena-${refreshKey}`} />}
          {tab === "roster" && <AgentRoster key={`roster-${refreshKey}`} />}
          {tab === "metrics" && <Metrics key={`metrics-${refreshKey}`} />}
        </main>
      </div>
    </div>
  );
}
