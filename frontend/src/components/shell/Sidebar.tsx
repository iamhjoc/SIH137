/**
 * Product-integrated navigation -- not a boring generic sidebar.
 * Uses a thin active-indicator rail + section grouping instead of
 * a flat list of pill buttons.
 */
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Activity, Sparkles, Route, Network, CloudFog,
  Truck, Users, BarChart3, FlaskConical, History, ShieldCheck, ChevronsLeft, Navigation,
} from "lucide-react";
import clsx from "clsx";
import { useAppStore } from "@/store/useAppStore";

const NAV = [
  {
    section: "Command",
    items: [
      { to: "/", label: "Overview", icon: LayoutDashboard },
      { to: "/operations", label: "Operations", icon: Activity },
      { to: "/directions", label: "Directions", icon: Navigation },
    ],
  },
  {
    section: "Optimize",
    items: [
      { to: "/optimization", label: "Optimization", icon: Sparkles },
      { to: "/routes", label: "Routes", icon: Route },
      { to: "/benchmarks", label: "Benchmarks", icon: BarChart3 },
      { to: "/experiments", label: "Experiments", icon: FlaskConical },
    ],
  },
  {
    section: "Data",
    items: [
      { to: "/network", label: "Network", icon: Network },
      { to: "/traffic", label: "Traffic", icon: CloudFog },
      { to: "/fleet", label: "Fleet", icon: Truck },
      { to: "/customers", label: "Customers", icon: Users },
    ],
  },
  {
    section: "System",
    items: [
      { to: "/history", label: "History", icon: History },
      { to: "/admin", label: "Administration", icon: ShieldCheck },
    ],
  },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

  return (
    <nav
      className={clsx(
        "shrink-0 border-r border-base-700 bg-base-950 flex flex-col transition-[width] duration-300",
        sidebarCollapsed ? "w-[64px]" : "w-[220px]",
      )}
      aria-label="Primary"
    >
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-5">
        {NAV.map((group) => (
          <div key={group.section}>
            {!sidebarCollapsed && <p className="label-caps px-2.5 mb-1.5">{group.section}</p>}
            <div className="space-y-0.5">
              {group.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    clsx(
                      "relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors group",
                      isActive ? "bg-base-850 text-ink-100" : "text-ink-500 hover:text-ink-100 hover:bg-base-900",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-signal" />
                      )}
                      <Icon size={16} className={isActive ? "text-signal" : ""} aria-hidden="true" />
                      {!sidebarCollapsed && <span>{label}</span>}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={toggleSidebar}
        aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="flex items-center gap-2 px-4 py-3 text-ink-700 hover:text-ink-300 text-xs border-t border-base-800"
      >
        <ChevronsLeft size={14} className={clsx("transition-transform", sidebarCollapsed && "rotate-180")} />
        {!sidebarCollapsed && "Collapse"}
      </button>
    </nav>
  );
}
