export default function PipelineDiagram() {
  return (
    <div className="bg-panel border border-border rounded-xl p-5 overflow-x-auto">
      <svg viewBox="0 0 780 260" className="w-full min-w-[700px]" style={{ maxHeight: 280 }}>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#565A75" />
          </marker>
          <marker id="arrowAccent" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#9B8CFF" />
          </marker>
        </defs>

        {/* Nodes */}
        <Node x={40} y={90} w={160} h={80} title="Identify" sub="Research agent + web search" color="#5B9CFF" />
        <Node x={310} y={90} w={160} h={80} title="Generate" sub="Synthetic attacks + content" color="#9B8CFF" />
        <Node x={580} y={90} w={160} h={80} title="Defend" sub="Router → specialists + generalist" color="#3DDC84" />

        {/* Forward flow */}
        <path d="M 200 130 L 305 130" stroke="#565A75" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />
        <path d="M 470 130 L 575 130" stroke="#565A75" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />

        {/* Feedback loop (the closed loop) */}
        <path
          d="M 660 170 C 660 230, 120 230, 120 170"
          stroke="#9B8CFF"
          strokeWidth="1.5"
          strokeDasharray="4 3"
          markerEnd="url(#arrowAccent)"
          fill="none"
        />
        <text x="390" y="248" textAnchor="middle" fontSize="11" fontFamily="IBM Plex Mono" fill="#9B8CFF">
          unclaimed anomalous cases → new pattern discovered → new specialist trained
        </text>

        {/* Adversarial loop (red vs blue) */}
        <path
          d="M 660 90 C 660 40, 660 40, 580 40"
          stroke="#FFB454"
          strokeWidth="1.5"
          strokeDasharray="4 3"
          markerEnd="url(#arrow)"
          fill="none"
        />
        <text x="620" y="30" textAnchor="middle" fontSize="10" fontFamily="IBM Plex Mono" fill="#FFB454">
          mutate to evade
        </text>
        <path d="M 580 40 C 500 40, 500 40, 470 90" stroke="#FFB454" strokeWidth="1.5" fill="none" markerEnd="url(#arrow)" />
      </svg>
      <div className="flex items-center gap-4 mt-2 text-[10px] font-mono text-faint">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-accent inline-block" /> discovery loop</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-warn inline-block" /> adversarial evolution loop</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-info inline-block" /> assure (Arena → RBI FREE-AI Rec 20)</span>
      </div>
    </div>
  );
}

function Node({ x, y, w, h, title, sub, color }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={10} fill="#161F29" stroke={color} strokeWidth="1.5" opacity="0.95" />
      <text x={x + w / 2} y={y + h / 2 - 6} textAnchor="middle" fontSize="15" fontFamily="Space Grotesk" fontWeight="600" fill="#ECEDF7">
        {title}
      </text>
      <text x={x + w / 2} y={y + h / 2 + 16} textAnchor="middle" fontSize="10" fontFamily="IBM Plex Mono" fill="#8B8FA8">
        {sub}
      </text>
    </g>
  );
}
