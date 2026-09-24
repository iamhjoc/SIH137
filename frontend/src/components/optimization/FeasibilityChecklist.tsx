/**
 * Visual pre-check sequence (section 15). Each check animates in as it
 * resolves. On failure, explains what/why/affected/action rather than a
 * bare red X.
 */
import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

export interface FeasibilityCheck {
  key: string;
  label: string;
  status: "pending" | "checking" | "pass" | "fail";
  detail?: string;
  failureExplanation?: { reason: string; affected: string[]; action: string };
}

export function FeasibilityChecklist({ checks, onResolveAction }: {
  checks: FeasibilityCheck[];
  onResolveAction?: (checkKey: string) => void;
}) {
  const allPass = checks.every((c) => c.status === "pass");

  return (
    <div className="space-y-2">
      {checks.map((check, i) => (
        <motion.div
          key={check.key}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.08, duration: 0.2 }}
          className="panel-inset p-3"
        >
          <div className="flex items-center gap-2.5">
            {check.status === "pass" && <CheckCircle2 size={16} className="text-traffic-normal shrink-0" />}
            {check.status === "fail" && <XCircle size={16} className="text-traffic-severe shrink-0" />}
            {(check.status === "checking" || check.status === "pending") && (
              <Loader2 size={16} className={`text-ink-500 shrink-0 ${check.status === "checking" ? "animate-spin" : "opacity-30"}`} />
            )}
            <span className="label-caps flex-1">{check.label}</span>
            {check.detail && <span className="text-xs text-ink-500">{check.detail}</span>}
          </div>

          {check.status === "fail" && check.failureExplanation && (
            <div className="mt-2.5 ml-6 pl-3 border-l-2 border-traffic-severe/40">
              <p className="text-sm text-ink-100">{check.failureExplanation.reason}</p>
              {check.failureExplanation.affected.length > 0 && (
                <p className="text-xs text-ink-500 mt-1">
                  Affected: {check.failureExplanation.affected.join(", ")}
                </p>
              )}
              <button onClick={() => onResolveAction?.(check.key)} className="btn-secondary text-xs mt-2">
                {check.failureExplanation.action}
              </button>
            </div>
          )}
        </motion.div>
      ))}

      {allPass && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center text-sm font-medium text-traffic-normal pt-2"
        >
          Ready for optimization
        </motion.div>
      )}
    </div>
  );
}
