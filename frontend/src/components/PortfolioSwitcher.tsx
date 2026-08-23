import { useState, type FormEvent } from "react";
import { usePortfolios } from "@/hooks/usePortfolios";

/** Chevron next to the "Portfolio" title: switch between named portfolios,
 * merge them ("Todos"), rename or create one (see docs/devlog/BACKLOG.md,
 * v3 item 1 -- organizational grouping, e.g. positions held at different
 * brokers, not a real per-portfolio permission boundary). */
export function PortfolioSwitcher() {
  const {
    portfolios,
    activeId,
    activePortfolio,
    setActiveId,
    createPortfolio,
    renamePortfolio,
  } = usePortfolios();
  const [open, setOpen] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);

  function close() {
    setOpen(false);
    setRenamingId(null);
    setCreating(false);
    setNewName("");
    setError(null);
  }

  function startRename(id: number, currentName: string) {
    setRenamingId(id);
    setRenameValue(currentName);
    setError(null);
  }

  async function submitRename(e: FormEvent) {
    e.preventDefault();
    if (renamingId === null) return;
    try {
      await renamePortfolio(renamingId, renameValue);
      setRenamingId(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo renombrar");
    }
  }

  async function submitCreate(e: FormEvent) {
    e.preventDefault();
    try {
      await createPortfolio(newName);
      close();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear");
    }
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 rounded-control px-1.5 py-0.5 text-secondary transition-colors duration-150 hover:bg-separator/40 hover:text-primary"
        aria-label="Cambiar de portfolio"
        title={activePortfolio ? activePortfolio.name : "Todos los portfolios"}
      >
        <span className="text-sm font-normal">
          {activePortfolio ? activePortfolio.name : "Todos"}
        </span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={close} />
          <div className="absolute left-0 top-full z-30 mt-2 w-64 rounded-control border border-separator bg-bg p-1.5 shadow-lg">
            <button
              onClick={() => {
                setActiveId(null);
                close();
              }}
              className={`flex w-full items-center justify-between rounded-control px-2.5 py-1.5 text-left text-sm transition-colors duration-150 hover:bg-separator/40 ${
                activeId === null ? "text-accent" : "text-primary"
              }`}
            >
              Todos
              <span className="text-[11px] text-secondary">mergeados</span>
            </button>

            <div className="my-1 border-t border-separator/60" />

            <ul className="max-h-64 overflow-y-auto">
              {portfolios.map((p) => (
                <li key={p.id}>
                  {renamingId === p.id ? (
                    <form onSubmit={submitRename} className="flex items-center gap-1 px-1 py-1">
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        className="w-full rounded-control border border-accent bg-bg px-2 py-1 text-sm text-primary focus:outline-none"
                      />
                      <button type="submit" className="shrink-0 rounded-control px-1.5 py-1 text-xs text-accent hover:bg-accent/10">
                        OK
                      </button>
                    </form>
                  ) : (
                    <div className="group flex items-center rounded-control hover:bg-separator/40">
                      <button
                        onClick={() => {
                          setActiveId(p.id);
                          close();
                        }}
                        className={`flex-1 truncate px-2.5 py-1.5 text-left text-sm transition-colors duration-150 ${
                          activeId === p.id ? "text-accent" : "text-primary"
                        }`}
                      >
                        {p.name}
                      </button>
                      <button
                        onClick={() => startRename(p.id, p.name)}
                        aria-label={`Renombrar ${p.name}`}
                        className="mr-1 shrink-0 rounded-control p-1 text-secondary opacity-0 transition-opacity duration-150 hover:text-primary group-hover:opacity-100"
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 20h9" />
                          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
                        </svg>
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>

            <div className="my-1 border-t border-separator/60" />

            {creating ? (
              <form onSubmit={submitCreate} className="flex items-center gap-1 px-1 py-1">
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Nombre del portfolio…"
                  className="w-full rounded-control border border-accent bg-bg px-2 py-1 text-sm text-primary focus:outline-none"
                />
                <button type="submit" className="shrink-0 rounded-control px-1.5 py-1 text-xs text-accent hover:bg-accent/10">
                  Crear
                </button>
              </form>
            ) : (
              <button
                onClick={() => setCreating(true)}
                className="flex w-full items-center gap-1.5 rounded-control px-2.5 py-1.5 text-left text-sm text-secondary transition-colors duration-150 hover:bg-separator/40 hover:text-primary"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Nuevo portfolio
              </button>
            )}

            {error && <p className="px-2.5 pt-1 text-xs text-loss">{error}</p>}
          </div>
        </>
      )}
    </div>
  );
}
