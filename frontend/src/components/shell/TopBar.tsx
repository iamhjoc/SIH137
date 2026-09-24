import { Bell, Search, User as UserIcon } from "lucide-react";
import { ContextSelector } from "./ContextSelector";

export function TopBar() {
  return (
    <header className="h-14 border-b border-base-700 bg-base-950/80 backdrop-blur-sm flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-sm bg-signal/15 border border-signal/30 flex items-center justify-center">
            <div className="h-1.5 w-1.5 rounded-full bg-signal animate-pulse-node" />
          </div>
          <span className="font-semibold text-sm tracking-tight">SIH26137</span>
        </div>
        <div className="h-4 w-px bg-base-700" />
        <ContextSelector />
      </div>

      <div className="flex items-center gap-1">
        <button aria-label="Search" className="p-2 rounded-md hover:bg-base-800 text-ink-500 hover:text-ink-100 transition-colors">
          <Search size={16} />
        </button>
        <button aria-label="Notifications" className="p-2 rounded-md hover:bg-base-800 text-ink-500 hover:text-ink-100 transition-colors">
          <Bell size={16} />
        </button>
        <div className="h-4 w-px bg-base-700 mx-1" />
        <button className="flex items-center gap-2 rounded-md pl-2 pr-3 py-1.5 hover:bg-base-800 transition-colors">
          <div className="h-6 w-6 rounded-full bg-base-700 flex items-center justify-center">
            <UserIcon size={13} className="text-ink-300" />
          </div>
          <span className="text-xs text-ink-500">Admin</span>
        </button>
      </div>
    </header>
  );
}
