/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0A0A12",
        panel: "#131320",
        panel2: "#181828",
        border: "#242438",
        ink: "#ECEDF7",
        muted: "#8B8FA8",
        // "faint" was #565A75, which computes to ~2.6:1 contrast against
        // panel/panel2 backgrounds -- well under WCAG AA's 4.5:1 minimum
        // for text. Lightened to a value that clears ~4.5:1 while staying
        // visually dimmer than "muted", preserving the intended
        // ink > muted > faint hierarchy without any tier being illegible.
        faint: "#7B80A0",
        // Brand accent: warm violet, distinctly non-green -- fits "Orion"
        // (night sky / nebula) without competing with the risk-tier colors.
        accent: "#9B8CFF",
        accentDim: "#6B5FCF",
        // Risk-tier colors stay universal red/amber/green, independent of brand accent.
        danger: "#FF5C6C",
        warn: "#FFB454",
        safe: "#3DDC84",
        info: "#5B9CFF",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
    },
  },
  plugins: [],
}
