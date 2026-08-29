const tierColor = (score) => {
  if (score >= 0.7) return "#FF5C6C";
  if (score >= 0.4) return "#FFB454";
  return "#3DDC84";
};

const tierLabel = (score) => {
  if (score >= 0.7) return "HIGH";
  if (score >= 0.4) return "MED";
  return "LOW";
};

// Semi-circle gauge: 180deg arc, needle-free, filled arc proportional to score.
export default function RiskGauge({ score = 0, size = 64, strokeWidth = 6, showLabel = true }) {
  const clamped = Math.max(0, Math.min(1, score));
  const color = tierColor(clamped);
  const radius = (size - strokeWidth) / 2;
  const circumference = Math.PI * radius; // half circumference (180deg arc)
  const dash = circumference * clamped;

  const cx = size / 2;
  const cy = size / 2;

  return (
    <div className="flex flex-col items-center gap-0.5" style={{ width: size }}>
      <svg width={size} height={size / 2 + strokeWidth / 2} viewBox={`0 0 ${size} ${size / 2 + strokeWidth / 2}`}>
        <path
          d={`M ${strokeWidth / 2} ${cy} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${cy}`}
          fill="none"
          stroke="#1E2733"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <path
          d={`M ${strokeWidth / 2} ${cy} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
          style={{ transition: "stroke-dasharray 0.5s ease, stroke 0.5s ease" }}
        />
        <text
          x={cx}
          y={cy - 2}
          textAnchor="middle"
          fontSize={size * 0.22}
          fontFamily="'IBM Plex Mono', monospace"
          fontWeight="600"
          fill="#E6EDF3"
        >
          {clamped.toFixed(2)}
        </text>
      </svg>
      {showLabel && (
        <span
          className="text-[9px] font-mono font-semibold tracking-wider"
          style={{ color }}
        >
          {tierLabel(clamped)}
        </span>
      )}
    </div>
  );
}

export { tierColor, tierLabel };
