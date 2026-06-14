import { NavLink } from "react-router-dom";
import { NAV_TABS } from "@/lib/nav";

/** Fixed vertical navigation sidebar (macOS/iPadOS style). */
export function Sidebar() {
  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-separator bg-surface/40 px-3 py-5">
      <div className="px-3 pb-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-control bg-accent text-sm font-bold text-white">
            C
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">CLARA</div>
            <div className="text-[11px] leading-tight text-secondary">
              Mesa de análisis
            </div>
          </div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_TABS.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path}
            end={tab.path === "/"}
            title={tab.question}
            className={({ isActive }) =>
              [
                "group flex items-center gap-3 rounded-control px-3 py-2 text-sm transition-colors duration-150",
                isActive
                  ? "bg-accent/15 text-primary"
                  : "text-secondary hover:bg-separator/50 hover:text-primary",
              ].join(" ")
            }
          >
            {({ isActive }) => (
              <>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke={isActive ? "#0A84FF" : "currentColor"}
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d={tab.icon} />
                </svg>
                <span className="truncate">{tab.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 pt-4 text-[11px] text-secondary">
        <span className="tabnum">v0.1.0</span> · dev
      </div>
    </aside>
  );
}
