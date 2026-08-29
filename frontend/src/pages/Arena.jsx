import { useEffect, useState, useCallback } from "react";
import { Swords, Trophy, Loader2, RotateCcw, ChevronDown } from "lucide-react";
import api from "../api";
import ErrorState from "../components/ErrorState";
import { tierColor } from "../components/RiskGauge";
import AssuranceSection from "../components/AssuranceSection";

export default function Arena() {
  const [scoreboard, setScoreboard] = useState(null);
  const [taxonomy, setTaxonomy] = useState([]);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [rounds, setRounds] = useState(5);
  const [fighting, setFighting] = useState(false);
  const [matchResult, setMatchResult] = useState(null);
  const [revealedCount, setRevealedCount] = useState(0);

  const loadScoreboard = useCallback(() => {
    api.scoreboard().then(setScoreboard).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    loadScoreboard();
    api.taxonomy().then((r) => {
      setTaxonomy(r.entries);
      setSelected(r.entries[0]?.attack_id || null);
    }).catch((e) => setError(e.message));
  }, [loadScoreboard]);

  const fight = async () => {
    if (!selected) return;
    setFighting(true);
    setMatchResult(null);
    setRevealedCount(0);
    try {
      const result = await api.runBattle(selected, rounds);
      setMatchResult(result);
      // Animate rounds appearing one at a time
      result.rounds.forEach((_, i) => {
        setTimeout(() => setRevealedCount((c) => Math.max(c, i + 1)), (i + 1) * 500);
      });
      setTimeout(loadScoreboard, (result.rounds.length + 1) * 500);
    } catch (e) {
      setError(e.message);
    } finally {
      setFighting(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("Reset the scoreboard? This clears all battle history.")) return;
    await api.resetScoreboard();
    setMatchResult(null);
    loadScoreboard();
  };

  if (error && !scoreboard) return <ErrorState message={error} onRetry={loadScoreboard} />;
  if (!scoreboard) return <div className="text-faint text-sm font-mono">loading arena…</div>;

  const redPct = scoreboard.total_battles ? (scoreboard.red_wins / scoreboard.total_battles) * 100 : 50;

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold flex items-center gap-2">
            <Swords size={20} className="text-warn" />
            Red vs Blue Arena
          </h2>
          <p className="text-sm text-muted mt-1">
            Every adversarial round — from here, Simulate, or Metrics — counts toward this scoreboard.
            Red wins when a mutated attack evades detection; blue wins when the detector holds.
          </p>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 text-xs font-mono text-faint hover:text-danger transition-colors shrink-0"
        >
          <RotateCcw size={12} /> reset
        </button>
      </div>

      {/* Big scoreboard */}
      <div className="bg-panel border border-border rounded-xl p-5">
        <div className="flex items-center justify-between gap-4">
          <TeamScore label="RED TEAM" sub="evasion" score={scoreboard.red_wins} color="#FF5C6C" align="left" />
          <div className="text-center shrink-0">
            <div className="text-[10px] font-mono text-faint uppercase tracking-wider">Total battles</div>
            <div className="text-2xl font-mono font-bold text-ink">{scoreboard.total_battles}</div>
          </div>
          <TeamScore label="BLUE TEAM" sub="detection held" score={scoreboard.blue_wins} color="#5B9CFF" align="right" />
        </div>
        {/* Win-rate bar */}
        <div className="mt-4 h-2.5 rounded-full overflow-hidden bg-panel2 flex">
          <div style={{ width: `${redPct}%`, background: "#FF5C6C" }} className="transition-all duration-500" />
          <div style={{ width: `${100 - redPct}%`, background: "#5B9CFF" }} className="transition-all duration-500" />
        </div>
      </div>

      {/* Fight controls */}
      <div className="bg-panel2 border border-border rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <select
              value={selected || ""}
              onChange={(e) => setSelected(e.target.value)}
              className="appearance-none bg-panel border border-border rounded-lg pl-3 pr-8 py-2 text-xs font-mono text-ink focus:border-accent outline-none"
            >
              {taxonomy.map((t) => (
                <option key={t.attack_id} value={t.attack_id}>{t.display_name}</option>
              ))}
            </select>
            <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-faint pointer-events-none" />
          </div>

          <div className="flex items-center gap-1.5">
            {[3, 5, 7].map((r) => (
              <button
                key={r}
                onClick={() => setRounds(r)}
                className={`text-xs font-mono px-2.5 py-1.5 rounded-lg border transition-colors ${
                  rounds === r ? "border-warn bg-warn/10 text-warn" : "border-border text-faint hover:text-muted"
                }`}
              >
                Bo{r}
              </button>
            ))}
          </div>

          <button
            onClick={fight}
            disabled={fighting || !selected}
            className="ml-auto flex items-center gap-2 bg-warn text-base font-display font-bold text-sm px-6 py-2.5 rounded-lg hover:bg-warn/90 disabled:opacity-50 transition-colors"
          >
            {fighting ? <Loader2 size={16} className="animate-spin" /> : <Swords size={16} />}
            FIGHT!
          </button>
        </div>
      </div>

      {/* Match result, animated round by round */}
      {matchResult && (
        <div className="bg-panel border border-border rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">
              Match: {taxonomy.find((t) => t.attack_id === matchResult.attack_id)?.display_name}
            </div>
            {revealedCount >= matchResult.rounds.length && (
              <MatchBanner winner={matchResult.winner} red={matchResult.red_wins} blue={matchResult.blue_wins} />
            )}
          </div>

          <div className="space-y-1.5">
            {matchResult.rounds.slice(0, revealedCount).map((r, i) => (
              <RoundRow key={i} index={i + 1} round={r} />
            ))}
          </div>
        </div>
      )}

      {/* Leaderboard */}
      <div>
        <div className="flex items-center gap-1.5 text-sm font-semibold mb-3">
          <Trophy size={16} className="text-warn" /> Leaderboard — toughest specialists
        </div>
        <p className="text-[10px] font-mono text-muted mb-3">
          Sorted by blue win rate, toughest first. Ranking answers "which specialist is hardest for the
          red team to fool" — a low number here is a real, discovered weakness in that specialist, not
          a scoring artifact.
        </p>
        {scoreboard.leaderboard.length === 0 ? (
          <div className="text-xs text-faint font-mono py-4">No battles fought yet — hit FIGHT! above.</div>
        ) : (
          <div className="space-y-1.5">
            {scoreboard.leaderboard.map((entry, i) => (
              <div key={entry.attack_id} className="flex items-center gap-3 bg-panel border border-border rounded-lg p-3">
                <div className="w-6 text-center text-xs font-mono text-muted shrink-0">#{i + 1}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm truncate">{entry.display_name}</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase ${entry.tier === "deep" ? "bg-safe/15 text-safe" : "bg-accent/15 text-accent"}`}>
                      {entry.tier}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-muted mt-0.5">
                    {entry.battles} battles · {entry.blue_wins}W-{entry.red_wins}L
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className={`text-sm font-mono font-semibold ${entry.blue_win_rate >= 0.5 ? "text-safe" : "text-danger"}`}>
                    {(entry.blue_win_rate * 100).toFixed(0)}%
                  </div>
                  <div className="text-[9px] font-mono text-muted">blue win rate</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Assure: RBI FREE-AI Rec 20 aligned periodic red-teaming audit */}
      <div className="border-t border-border pt-6">
        <AssuranceSection />
      </div>
    </div>
  );
}

function TeamScore({ label, sub, score, color, align }) {
  return (
    <div className={`flex-1 ${align === "right" ? "text-right" : "text-left"}`}>
      <div className="text-[10px] font-mono uppercase tracking-wider" style={{ color }}>{label}</div>
      <div className="text-4xl font-mono font-bold" style={{ color }}>{score}</div>
      <div className="text-[10px] font-mono text-faint">{sub}</div>
    </div>
  );
}

function MatchBanner({ winner, red, blue }) {
  const label = winner === "red" ? "RED TEAM WINS" : winner === "blue" ? "BLUE TEAM WINS" : winner === "draw" ? "DRAW" : "INCONCLUSIVE";
  const color = winner === "red" ? "text-danger bg-danger/10 border-danger/30" : winner === "blue" ? "text-safe bg-safe/10 border-safe/30" : "text-faint bg-panel2 border-border";
  return (
    <span className={`text-xs font-mono font-bold px-3 py-1 rounded-lg border ${color}`}>
      {label} ({blue}-{red})
    </span>
  );
}

function RoundRow({ index, round }) {
  if (!round.round_2) {
    return (
      <div className="flex items-center gap-3 text-xs font-mono text-faint bg-panel2/60 rounded-lg px-3 py-2 animate-[fadeIn_0.3s_ease]">
        <span className="w-5 shrink-0">R{index}</span>
        <span>{round.mutation?.reason || "no evasion attempt"}</span>
      </div>
    );
  }
  const evaded = round.mutation.evaded;
  return (
    <div className="flex items-center gap-3 text-xs font-mono bg-panel2/60 rounded-lg px-3 py-2 animate-[fadeIn_0.3s_ease]">
      <span className="w-5 shrink-0 text-faint">R{index}</span>
      <span style={{ color: tierColor(round.round_1.final_risk_score) }}>{round.round_1.final_risk_score.toFixed(2)}</span>
      <span className="text-faint">→</span>
      <span style={{ color: tierColor(round.round_2.final_risk_score) }}>{round.round_2.final_risk_score.toFixed(2)}</span>
      <span className={`ml-auto font-semibold ${evaded ? "text-danger" : "text-safe"}`}>
        {evaded ? "RED WINS" : "BLUE HOLDS"}
      </span>
    </div>
  );
}
