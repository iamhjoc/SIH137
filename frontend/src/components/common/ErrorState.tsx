/**
 * Errors are first-class UI, not toasts-only. Every error explains
 * what happened, why, and what the user can do next.
 */
import { AlertOctagon, RefreshCw } from "lucide-react";

interface Props {
  title: string;
  reason?: string;
  action?: { label: string; onClick: () => void };
}

export function ErrorState({ title, reason, action }: Props) {
  return (
    <div className="panel p-6 border-traffic-severe/30">
      <div className="flex items-start gap-3">
        <AlertOctagon className="text-traffic-severe shrink-0 mt-0.5" size={20} aria-hidden="true" />
        <div className="flex-1">
          <p className="font-medium text-ink-100">{title}</p>
          {reason && <p className="text-sm text-ink-500 mt-1">{reason}</p>}
          {action && (
            <button onClick={action.onClick} className="btn-secondary mt-4 text-xs">
              <RefreshCw size={13} /> {action.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
