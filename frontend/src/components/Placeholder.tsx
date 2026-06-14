import { Card } from "./Card";

/** Empty-state used by tabs that aren't built yet (Phase 0 shell). */
export function Placeholder({ phase }: { phase: string }) {
  return (
    <Card>
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full border border-separator text-secondary">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-primary">En construcción</p>
        <p className="max-w-sm text-xs text-secondary">
          Esta pestaña se completa en {phase}. El shell, la navegación y el
          theme ya están en su lugar.
        </p>
      </div>
    </Card>
  );
}
