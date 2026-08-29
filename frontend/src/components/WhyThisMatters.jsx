import { ExternalLink, TrendingUp, FileText } from "lucide-react";

// Only globally-scoped figures here -- no geographic-mismatch caveats
// needed. Region-specific numbers (which do need that context) live in
// RESEARCH.md, not on a stat card. A product page states clean facts;
// methodology caveats belong in the methodology doc, not a warning icon
// bolted onto every number.
const STATS = [
  {
    value: "$485B+",
    label: "global fraud impact, 2024",
    source: "Mastercard research, via Mastercard.com (2026)",
    url: "https://www.mastercard.com/global/en/news-and-trends/Insights/2026/ai-is-helping-banks-save-millions-by-transforming-payment-fraud-prevention.html",
  },
  {
    value: "$60M",
    label: "average annual fraud loss per organization",
    source: "Mastercard research, via Mastercard.com (2026)",
    url: "https://www.mastercard.com/global/en/news-and-trends/Insights/2026/ai-is-helping-banks-save-millions-by-transforming-payment-fraud-prevention.html",
  },
];

export default function WhyThisMatters() {
  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm font-semibold flex items-center gap-1.5">
          <TrendingUp size={16} className="text-accent" /> Why this matters
        </div>
        <p className="text-xs text-muted mt-1.5 leading-relaxed max-w-2xl">
          Mastercard's own generative-AI fraud systems are reported to generate synthetic fraudulent
          transaction data for two purposes: training detection models, and proactively probing
          partner banks' systems for vulnerabilities before real criminals find them. Orion's Generate
          pillar and Adversarial Evolution loop follow the same underlying philosophy, arrived at
          independently and at a much smaller scale — not a claim of parity with Mastercard's
          trillion-transaction Decision Intelligence platform, but a distilled, explainable version of
          that approach built to run without network-scale data — the kind of thing a smaller bank,
          NBFC, or fintech partner (most of any GFF audience) could realistically operate.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {STATS.map((s) => (
          <div key={s.label} className="bg-panel border border-border rounded-xl p-3.5">
            <div className="text-xl font-mono font-bold text-accent">{s.value}</div>
            <div className="text-xs text-muted mt-1 leading-snug">{s.label}</div>
            <a
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="text-[10px] font-mono text-info hover:underline flex items-center gap-1 mt-2"
            >
              <ExternalLink size={9} />
              {s.source}
            </a>
          </div>
        ))}
      </div>

      <div
        className="text-[10px] font-mono text-faint flex items-center gap-1.5 w-fit"
        title="Full sourcing, region-specific caveats, and methodology notes are in RESEARCH.md in the repo"
      >
        <FileText size={10} />
        Full sourcing &amp; methodology notes — see RESEARCH.md
      </div>
    </div>
  );
}
