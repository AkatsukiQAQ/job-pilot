// Hand-drawn-style stacked bar for status distribution; mirrors docs/design/v1/dashboard-v1's distChart().
const WOBBLE = [0, 0.5, -0.4, 0.3];

export interface DistributionSegment {
  key: string;
  count: number;
  color: string;
}

export function DistributionBar({
  segments,
  total,
  ariaLabel,
}: {
  segments: DistributionSegment[];
  total: number;
  ariaLabel: string;
}) {
  if (total <= 0) return null;
  let x = 0;
  return (
    <svg role="img" aria-label={ariaLabel} viewBox="0 0 100 18" preserveAspectRatio="none" className="h-[18px] w-full">
      {segments.map((s, i) => {
        const width = (s.count / total) * 100;
        const rect = (
          <rect
            key={s.key}
            x={x}
            y={1 + WOBBLE[i % WOBBLE.length]}
            width={width}
            height={12}
            rx={1.4}
            fill={s.color}
            stroke="var(--color-ink-900)"
            strokeWidth={1.2}
            vectorEffect="non-scaling-stroke"
          />
        );
        x += width;
        return rect;
      })}
      <line
        x1={0}
        y1={16.5}
        x2={100}
        y2={16.5}
        stroke="var(--color-ink-200)"
        strokeWidth={1}
        strokeDasharray="3 4"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
