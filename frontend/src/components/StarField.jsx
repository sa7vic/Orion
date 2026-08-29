import { useMemo } from "react";

// Deterministic pseudo-random so the layout doesn't reshuffle on every
// re-render (would be distracting behind scrolling content).
function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// A handful of stars are grouped into small constellation clusters with
// thin connecting lines -- a nod to "Orion" without literally drawing the
// belt, kept abstract so it reads as texture, not iconography.
function buildField(width, height, seed) {
  const rand = mulberry32(seed);
  const stars = [];
  const count = 70;
  for (let i = 0; i < count; i++) {
    stars.push({
      x: rand() * width,
      y: rand() * height,
      r: 0.6 + rand() * 1.6,
      o: 0.15 + rand() * 0.45,
    });
  }
  // Build 4 small clusters of 3-4 nearby stars and connect them with lines.
  const clusters = [];
  for (let c = 0; c < 4; c++) {
    const cx = rand() * width;
    const cy = rand() * height;
    const pts = [];
    const n = 3 + Math.floor(rand() * 2);
    for (let i = 0; i < n; i++) {
      pts.push({
        x: cx + (rand() - 0.5) * 160,
        y: cy + (rand() - 0.5) * 160,
      });
    }
    clusters.push(pts);
  }
  return { stars, clusters };
}

export default function StarField() {
  const { stars, clusters } = useMemo(() => buildField(1600, 1000, 42), []);

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none select-none">
      <svg
        className="w-full h-full"
        viewBox="0 0 1600 1000"
        preserveAspectRatio="xMidYMid slice"
      >
        {clusters.map((pts, ci) => (
          <g key={ci}>
            {pts.slice(1).map((p, i) => (
              <line
                key={i}
                x1={pts[0].x}
                y1={pts[0].y}
                x2={p.x}
                y2={p.y}
                stroke="#9B8CFF"
                strokeWidth="0.6"
                opacity="0.12"
              />
            ))}
            {pts.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r="1.4" fill="#9B8CFF" opacity="0.35" />
            ))}
          </g>
        ))}
        {stars.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="#ECEDF7" opacity={s.o} />
        ))}
      </svg>
    </div>
  );
}
