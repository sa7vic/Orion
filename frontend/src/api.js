const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  taxonomy: () => request("/api/taxonomy"),
  agents: () => request("/api/agents"),
  simulate: (attack_id, n = 1) =>
    request("/api/simulate", { method: "POST", body: JSON.stringify({ attack_id, n }) }),
  detect: (payload) =>
    request("/api/detect", { method: "POST", body: JSON.stringify(payload) }),
  feed: (limit = 30) => request(`/api/feed?limit=${limit}`),
  fidelity: (attack_id) => request(`/api/fidelity/${attack_id}`),
  metrics: () => request("/api/metrics"),
  pendingClusters: () => request("/api/feedback/pending"),
  forcePromote: (channel, sample_summaries) =>
    request("/api/feedback/force-promote", {
      method: "POST",
      body: JSON.stringify({ channel, sample_summaries }),
    }),
  reset: () => request("/api/reset", { method: "POST" }),
  researchPattern: (attack_id) =>
    request(`/api/identify/research/${attack_id}`, { method: "POST" }),
  evolveAttack: (attack_id) =>
    request(`/api/adversarial/evolve/${attack_id}`, { method: "POST" }),
  thresholdCurve: (attack_id) =>
    request(`/api/metrics/threshold-curve/${attack_id}`),
  evaluationRegimes: (attack_id) =>
    request(`/api/metrics/evaluation-regimes/${attack_id}`),
  runBattle: (attack_id, rounds = 5) =>
    request(`/api/arena/battle/${attack_id}?rounds=${rounds}`, { method: "POST" }),
  scoreboard: () => request("/api/arena/scoreboard"),
  resetScoreboard: () => request("/api/arena/scoreboard/reset", { method: "POST" }),
  runAudit: (rounds_per_attack = 3) =>
    request(`/api/audit/run?rounds_per_attack=${rounds_per_attack}`, { method: "POST" }),
  auditHistory: () => request("/api/audit/history"),
  latestAudit: () => request("/api/audit/latest"),
  fullAssuranceReport: (rounds_per_attack = 3) =>
    request(`/api/audit/full-report?rounds_per_attack=${rounds_per_attack}`, { method: "POST" }),
};

export default api;
