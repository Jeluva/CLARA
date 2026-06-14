import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
}

/** Base surface for content. Rounded, subtle shadow, generous padding. */
export function Card({ title, subtitle, action, children, className }: CardProps) {
  return (
    <section
      className={[
        "rounded-card border border-separator bg-surface p-5 shadow-card",
        className ?? "",
      ].join(" ")}
    >
      {(title || action) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && (
              <h2 className="text-sm font-semibold text-primary">{title}</h2>
            )}
            {subtitle && (
              <p className="mt-0.5 text-xs text-secondary">{subtitle}</p>
            )}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
