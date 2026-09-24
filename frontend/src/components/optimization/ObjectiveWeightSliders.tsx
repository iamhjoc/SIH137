/**
 * Intelligent objective-balance sliders with named presets. Presets set
 * all weights at once; manually adjusting any slider switches the active
 * preset to "Custom" so the label never lies about the current state.
 */
import type { ObjectiveWeights } from "@/types/api";

const PRESETS: Record<string, ObjectiveWeights> = {
  Fastest: { distance: 0.15, time: 0.55, congestion: 0.2, late: 0.1, vehicle: 0, constraint: 1 },
  "Lowest Cost": { distance: 0.4, time: 0.2, congestion: 0.1, late: 0.05, vehicle: 0.25, constraint: 1 },
  "Lowest Congestion": { distance: 0.15, time: 0.2, congestion: 0.55, late: 0.1, vehicle: 0, constraint: 1 },
  Balanced: { distance: 0.25, time: 0.4, congestion: 0.25, late: 0.1, vehicle: 0, constraint: 1 },
};

const FIELDS: { key: keyof ObjectiveWeights; label: string }[] = [
  { key: "distance", label: "Distance" },
  { key: "time", label: "Travel Time" },
  { key: "congestion", label: "Congestion" },
  { key: "late", label: "Late Penalty" },
  { key: "vehicle", label: "Vehicle Cost" },
];

interface Props {
  weights: ObjectiveWeights;
  onChange: (weights: ObjectiveWeights) => void;
  activePreset: string | null;
  onPresetChange: (preset: string | null) => void;
}

export function ObjectiveWeightSliders({ weights, onChange, activePreset, onPresetChange }: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="label-caps">Objective Balance</span>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-4">
        {Object.keys(PRESETS).map((preset) => (
          <button
            key={preset}
            onClick={() => {
              onChange(PRESETS[preset]);
              onPresetChange(preset);
            }}
            className={`text-xs px-2.5 py-1 rounded-sm border transition-colors ${
              activePreset === preset
                ? "border-signal/40 bg-signal/10 text-signal"
                : "border-base-600 text-ink-500 hover:text-ink-100"
            }`}
          >
            {preset}
          </button>
        ))}
        <span
          className={`text-xs px-2.5 py-1 rounded-sm border ${
            activePreset === null ? "border-signal/40 bg-signal/10 text-signal" : "border-base-700 text-ink-700"
          }`}
        >
          Custom
        </span>
      </div>

      <div className="space-y-3">
        {FIELDS.map(({ key, label }) => {
          const pct = Math.round(weights[key] * 100);
          return (
            <div key={key}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-ink-300">{label}</span>
                <span className="text-ink-500 tabular-nums">{pct}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={pct}
                onChange={(e) => {
                  onChange({ ...weights, [key]: Number(e.target.value) / 100 });
                  onPresetChange(null);
                }}
                className="w-full accent-signal h-1.5"
                aria-label={`${label} weight`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
