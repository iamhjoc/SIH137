/**
 * Smoothly interpolates a numeric KPI value on change instead of snapping,
 * per the "animated KPI transitions" requirement. Respects reduced-motion.
 */
import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";

interface Props {
  value: number;
  decimals?: number;
  suffix?: string;
  durationMs?: number;
}

export function AnimatedNumber({ value, decimals = 0, suffix = "", durationMs = 500 }: Props) {
  const [display, setDisplay] = useState(value);
  const prevValue = useRef(value);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion) {
      setDisplay(value);
      prevValue.current = value;
      return;
    }
    const start = prevValue.current;
    const delta = value - start;
    const startTime = performance.now();
    let raf: number;

    const tick = (now: number) => {
      const t = Math.min((now - startTime) / durationMs, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setDisplay(start + delta * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
      else prevValue.current = value;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, durationMs, reducedMotion]);

  return (
    <span className="tabular-nums">
      {display.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}
