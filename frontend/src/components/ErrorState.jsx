import { AlertTriangle, RefreshCw } from "lucide-react";

export default function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3 text-center max-w-md mx-auto">
      <AlertTriangle size={28} className="text-danger" strokeWidth={1.5} />
      <div className="text-sm text-ink font-medium">Couldn't reach the backend</div>
      <p className="text-xs text-muted leading-relaxed">
        {message || "Request failed."} Check that the backend is running
        (<code className="font-mono text-faint">uvicorn app.main:app --port 8000</code>) and that{" "}
        <code className="font-mono text-faint">frontend/.env</code>'s{" "}
        <code className="font-mono text-faint">VITE_API_URL</code> points at it.
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 text-xs font-mono text-accent border border-accent/40 px-3 py-1.5 rounded-lg hover:bg-accent/10 transition-colors"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      )}
    </div>
  );
}
