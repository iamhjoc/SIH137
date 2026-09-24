import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import type { ConvergencePoint } from "@/hooks/useOptimizationJob";

export function ConvergenceChart({ data }: { data: ConvergencePoint[] }) {
  if (data.length === 0) {
    return <div className="h-48 flex items-center justify-center text-sm text-ink-700">Awaiting first iteration…</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={192}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="convergenceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#5eead4" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#5eead4" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#22262d" vertical={false} />
        <XAxis dataKey="iteration" tick={{ fill: "#5a616d", fontSize: 11 }} axisLine={{ stroke: "#22262d" }} tickLine={false} />
        <YAxis tick={{ fill: "#5a616d", fontSize: 11 }} axisLine={false} tickLine={false} width={56} />
        <Tooltip
          contentStyle={{ background: "#121418", border: "1px solid #22262d", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#8a919e" }}
        />
        <Area type="monotone" dataKey="bestCost" stroke="#5eead4" strokeWidth={2} fill="url(#convergenceFill)" isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
