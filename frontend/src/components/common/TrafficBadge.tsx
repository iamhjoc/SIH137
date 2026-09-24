/**
 * Semantic traffic-state indicator. Never relies on color alone --
 * always paired with a label + icon shape so it reads for colorblind
 * users and in screen readers.
 */
import { AlertTriangle, CheckCircle2, TriangleAlert, Flame, Siren } from "lucide-react";
import clsx from "clsx";

export type TrafficState = "normal" | "moderate" | "heavy" | "severe" | "critical";

const CONFIG: Record<TrafficState, { label: string; color: string; icon: React.ElementType }> = {
  normal: { label: "Normal", color: "text-traffic-normal border-traffic-normal/30 bg-traffic-normal/10", icon: CheckCircle2 },
  moderate: { label: "Moderate", color: "text-traffic-moderate border-traffic-moderate/30 bg-traffic-moderate/10", icon: AlertTriangle },
  heavy: { label: "Heavy", color: "text-traffic-heavy border-traffic-heavy/30 bg-traffic-heavy/10", icon: TriangleAlert },
  severe: { label: "Severe", color: "text-traffic-severe border-traffic-severe/30 bg-traffic-severe/10", icon: Flame },
  critical: { label: "Critical", color: "text-traffic-critical border-traffic-critical/30 bg-traffic-critical/10", icon: Siren },
};

export function congestionToState(factor: number): TrafficState {
  // factor: 1.0 = free flow ... lower = worse congestion
  if (factor >= 0.85) return "normal";
  if (factor >= 0.65) return "moderate";
  if (factor >= 0.45) return "heavy";
  if (factor >= 0.25) return "severe";
  return "critical";
}

export function TrafficBadge({ state }: { state: TrafficState }) {
  const cfg = CONFIG[state];
  const Icon = cfg.icon;
  return (
    <span
      role="status"
      aria-label={`Traffic state: ${cfg.label}`}
      className={clsx("inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium", cfg.color)}
    >
      <Icon size={12} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}
