import type { HTMLAttributes, ReactNode } from 'react';

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hoverable?: boolean;
}

/** .card-paper (tokens.css): cream-50 surface, 1px ink-200 border, 14px radius, warm shadow. */
export function PaperCard({ children, hoverable, className, ...rest }: Props) {
  return (
    <div
      {...rest}
      className={[
        'card-paper p-5',
        hoverable
          ? 'cursor-pointer transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md'
          : '',
        className ?? '',
      ].join(' ')}
    >
      {children}
    </div>
  );
}
