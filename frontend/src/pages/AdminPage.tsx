/**
 * Administration. This app has no authentication or user-management
 * backend yet (see the project README) -- so unlike every other page in
 * this pass, there's no real endpoint to wire this to. The previous
 * version of this page showed a fabricated user table; showing nothing
 * real is more honest than showing something fake, so this is a plain
 * "not built yet" state instead.
 */
import { EmptyState } from "@/components/common/EmptyState";
import { ShieldCheck } from "lucide-react";

export function AdminPage() {
  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold mb-1">Administration</h1>
      <p className="text-sm text-ink-500 mb-4">Users, roles, and organization settings.</p>
      <EmptyState
        title="NOT YET BUILT"
        description="This app doesn't have authentication or a user-management API yet -- every request currently runs as a single hardcoded ADMIN principal (see core/dependencies.py on the backend). There's nothing real to show here until that exists."
        icon={<ShieldCheck size={28} />}
      />
    </div>
  );
}
