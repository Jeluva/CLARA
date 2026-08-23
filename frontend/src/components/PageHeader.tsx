import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  question: string;
  /** Rendered next to the title as a sibling of the <h1>, not inside it --
   * keeps the heading's accessible name just `title` (e.g. the portfolio
   * switcher chevron on the Portfolio tab). */
  adornment?: ReactNode;
}

/** Title block at the top of each tab. The question states the tab's purpose. */
export function PageHeader({ title, question, adornment }: PageHeaderProps) {
  return (
    <header className="mb-6">
      <div className="flex items-center gap-1.5">
        <h1 className="text-xl font-semibold tracking-tight text-primary">
          {title}
        </h1>
        {adornment}
      </div>
      <p className="mt-1 text-sm text-secondary">{question}</p>
    </header>
  );
}
