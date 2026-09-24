import { motion } from "framer-motion";
import { AnimatedNumber } from "./AnimatedNumber";
import type { LucideIcon } from "lucide-react";
import clsx from "clsx";

interface Props {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
  icon: LucideIcon;
  delta?: { value: number; direction: "up" | "down"; positiveIsGood?: boolean };
}

export function KpiCard({ label, value, decimals, suffix, icon: Icon, delta }: Props) {
  const deltaGood = delta && (delta.positiveIsGood ?? true ? delta.direction === "up" : delta.direction === "down");

  return (
    <motion.div
      className="panel p-4 flex flex-col gap-3"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="flex items-center justify-between">
        <span className="label-caps">{label}</span>
        <Icon size={15} className="text-ink-700" aria-hidden="true" />
      </div>
      <div className="flex items-end justify-between">
        <span className="text-2xl font-semibold text-ink-100">
          <AnimatedNumber value={value} decimals={decimals} suffix={suffix} />
        </span>
        {delta && (
          <span
            className={clsx(
              "text-xs font-medium flex items-center gap-0.5",
              deltaGood ? "text-traffic-normal" : "text-traffic-severe",
            )}
          >
            {delta.direction === "up" ? "↑" : "↓"} {delta.value}%
          </span>
        )}
      </div>
    </motion.div>
  );
}
