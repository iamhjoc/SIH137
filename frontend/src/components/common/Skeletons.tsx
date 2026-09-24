import clsx from "clsx";

function shimmer(className: string) {
  return <div className={clsx("animate-pulse rounded-md bg-base-800", className)} />;
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          {shimmer("h-8 w-1/4")}
          {shimmer("h-8 w-1/4")}
          {shimmer("h-8 w-1/6")}
          {shimmer("h-8 w-1/6")}
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="h-64 flex items-end gap-1.5 px-2">
      {Array.from({ length: 24 }).map((_, i) => (
        <div
          key={i}
          className="flex-1 animate-pulse rounded-t-sm bg-base-800"
          style={{ height: `${20 + ((i * 37) % 60)}%` }}
        />
      ))}
    </div>
  );
}

export function MapSkeleton() {
  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg bg-base-900 bg-grid-fine bg-[length:28px_28px]">
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="h-10 w-10 rounded-full border-2 border-base-700 border-t-signal animate-spin" />
      </div>
    </div>
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="panel p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        {shimmer("h-3 w-16")}
        {shimmer("h-4 w-4")}
      </div>
      {shimmer("h-7 w-14")}
    </div>
  );
}
