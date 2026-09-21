// Pill-shaped exclusive toggle group (filters, tabs); pressed state via aria-pressed.
interface Props<T extends string> {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; count?: number }[];
  ariaLabel: string;
  size?: 'sm' | 'md';
}

export function Segmented<T extends string>({ value, onChange, options, ariaLabel, size = 'md' }: Props<T>) {
  const sm = size === 'sm';
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={[
        'inline-flex rounded-full border border-cream-200 bg-cream-100',
        sm ? 'p-0.5 text-xs' : 'p-1 text-sm',
      ].join(' ')}
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className={[
            'inline-flex items-center rounded-full transition-colors',
            sm ? 'h-7 px-2.5' : 'h-8 px-3',
            value === o.value ? 'bg-cream-300 text-ink-900 font-medium' : 'text-ink-500 hover:text-ink-700',
          ].join(' ')}
        >
          {o.label}
          {o.count !== undefined ? <span className="ml-1.5 font-mono text-[11px] text-ink-500">{o.count}</span> : null}
        </button>
      ))}
    </div>
  );
}
