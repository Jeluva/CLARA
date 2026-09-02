import { useEffect, useRef, useState, type FormEvent } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { NAV_TABS } from "@/lib/nav";
import { getAlerts, type Alert } from "@/lib/api";

/** Type any ticker and jump straight to its detail page — no need to hold
 * a position (or even have the asset loaded yet) to look it up. */
function TickerSearch() {
  const [value, setValue] = useState("");
  const navigate = useNavigate();

  function submit(e: FormEvent) {
    e.preventDefault();
    const ticker = value.trim().toUpperCase();
    if (!ticker) return;
    navigate(`/activo/${ticker}`);
    setValue("");
  }

  return (
    <form onSubmit={submit} className="hidden sm:block">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Buscar ticker…"
        aria-label="Buscar ticker"
        className="w-36 rounded-control border border-separator bg-bg px-3 py-1.5 text-sm text-primary placeholder:text-secondary focus:border-accent focus:outline-none transition-colors duration-150"
      />
    </form>
  );
}

/** Alertas disparadas (precio/sentimiento/valuación) visibles desde
 * cualquier pestaña — el punto de las alertas es no depender de entrar a
 * mirar cada activo a mano (docs/devlog/BACKLOG.md, v2 item 8). */
function AlertsBadge() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getAlerts({ onlyTriggered: true })
      .then(setAlerts)
      .catch(() => setAlerts([]));
  }, []);

  // TopNav lives above <Routes>, so this "open" state survives route
  // changes on its own — without this, opening the panel once and then
  // navigating (e.g. to the chat tab) leaves it floating over whatever
  // page you land on next, no matter the window size.
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  // Close on outside click / Escape — otherwise the panel stays open and,
  // since it has no scroll cap, can grow tall enough to cover whatever page
  // content sits right below the header (e.g. the chat tab).
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (alerts.length === 0) return null;

  return (
    <div className="relative" ref={rootRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-control bg-loss/15 px-2.5 py-1 text-xs font-medium text-loss transition-colors duration-150 hover:bg-loss/25"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-loss" />
        {alerts.length} {alerts.length === 1 ? "alerta" : "alertas"}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 max-h-80 w-72 overflow-y-auto rounded-control border border-separator bg-bg p-2 shadow-lg">
          <ul className="divide-y divide-separator/60">
            {alerts.map((a) => (
              <li key={a.id}>
                <button
                  onClick={() => {
                    setOpen(false);
                    navigate(`/activo/${a.ticker}`);
                  }}
                  className="block w-full rounded-control px-2 py-2 text-left text-xs transition-colors duration-150 hover:bg-separator/40"
                >
                  <span className="font-medium text-primary">{a.ticker}</span>{" "}
                  <span className="text-secondary">
                    {a.metric} {a.condition === "above" ? "≥" : "≤"} {a.threshold}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Horizontal top navigation bar (replaces the old sidebar). */
export function TopNav() {
  return (
    <header className="sticky top-0 z-20 border-b border-separator bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:gap-4 sm:px-6">
        {/* Brand */}
        <div className="flex shrink-0 items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-control bg-accent text-sm font-bold text-white">
            C
          </div>
          <span className="hidden text-sm font-semibold md:inline">CLARA</span>
        </div>

        {/* Tabs — icon-only until there's room for labels too, so the bar
         * never has to wrap or scroll (user feedback: must stay in one row). */}
        <nav className="flex min-w-0 flex-1 items-center gap-0.5 sm:gap-1">
          {NAV_TABS.map((tab) => (
            <NavLink
              key={tab.path}
              to={tab.path}
              end={tab.path === "/"}
              title={tab.question}
              className={({ isActive }) =>
                [
                  "flex items-center gap-1.5 whitespace-nowrap rounded-control px-2 py-1.5 text-sm transition-colors duration-150 lg:px-3",
                  isActive
                    ? "bg-accent/15 text-primary"
                    : "text-secondary hover:bg-separator/50 hover:text-primary",
                ].join(" ")
              }
            >
              {({ isActive }) => (
                <>
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke={isActive ? "#0A84FF" : "currentColor"}
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="shrink-0"
                  >
                    <path d={tab.icon} />
                  </svg>
                  <span className="hidden lg:inline">{tab.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <AlertsBadge />
        <TickerSearch />

        <span className="tabnum hidden shrink-0 text-[11px] text-secondary xl:inline">
          v0.1.0 · dev
        </span>
      </div>
    </header>
  );
}
