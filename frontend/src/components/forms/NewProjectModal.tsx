import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Modal } from "@/components/common/Modal";
import { projectsApi } from "@/api/projects";
import { useAppStore } from "@/store/useAppStore";
import { ApiError } from "@/api/client";

export function NewProjectButton() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const queryClient = useQueryClient();
  const setContext = useAppStore((s) => s.setContext);

  const mutation = useMutation({
    mutationFn: () => projectsApi.create(name.trim(), timezone.trim() || "UTC"),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      // Immediately switch context to the new project so the user lands
      // somewhere useful instead of staying on whatever was previously
      // selected (or nothing, on a first run).
      setContext({ currentProjectId: project.id, currentGraphVersionId: null, currentTrafficScenarioId: null });
      setOpen(false);
      setName("");
      setTimezone("UTC");
    },
  });

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center justify-center rounded-md w-6 h-6 text-ink-500 hover:text-ink-100 hover:bg-base-800 transition-colors"
        aria-label="New project"
        title="New project"
      >
        <Plus size={14} />
      </button>

      <Modal open={open} title="New Project" onClose={() => setOpen(false)}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!name.trim()) return;
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <label className="label-caps block mb-1.5" htmlFor="project-name">Name</label>
            <input
              id="project-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Ludhiana Delivery Optimization"
              className="input-field w-full"
              autoFocus
              required
            />
          </div>
          <div>
            <label className="label-caps block mb-1.5" htmlFor="project-timezone">Timezone</label>
            <input
              id="project-timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="UTC"
              className="input-field w-full"
            />
          </div>
          {mutation.isError && (
            <p className="text-xs text-traffic-severe">
              {mutation.error instanceof ApiError ? mutation.error.message : "Failed to create project."}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={() => setOpen(false)} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={mutation.isPending || !name.trim()} className="btn-primary">
              {mutation.isPending ? "Creating…" : "Create Project"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
