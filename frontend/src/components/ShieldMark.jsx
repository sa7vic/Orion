export default function ShieldMark({ size = 28, pulsing = true }) {
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <path
          d="M16 2 L28 7 V15 C28 22.5 22.8 27.5 16 30 C9.2 27.5 4 22.5 4 15 V7 Z"
          fill="#111820"
          stroke="#9B8CFF"
          strokeWidth="1.5"
        />
        <path
          d="M11.5 16.2 L14.5 19.2 L20.5 12.5"
          stroke="#9B8CFF"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {pulsing && (
        <span className="absolute top-1 right-0.5 w-1.5 h-1.5 rounded-full bg-accent">
          <span className="absolute inset-0 rounded-full bg-accent animate-ping opacity-75" />
        </span>
      )}
    </div>
  );
}
