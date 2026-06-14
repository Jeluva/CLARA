interface PageHeaderProps {
  title: string;
  question: string;
}

/** Title block at the top of each tab. The question states the tab's purpose. */
export function PageHeader({ title, question }: PageHeaderProps) {
  return (
    <header className="mb-6">
      <h1 className="text-xl font-semibold tracking-tight text-primary">
        {title}
      </h1>
      <p className="mt-1 text-sm text-secondary">{question}</p>
    </header>
  );
}
