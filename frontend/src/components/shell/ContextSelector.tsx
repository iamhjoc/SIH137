/**
 * Context-aware selector: Organization -> Project -> Network Version ->
 * Traffic Scenario. Drives which data every other screen queries.
 */
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { projectsApi } from "@/api/projects";
import { trafficApi } from "@/api/traffic";
import { useAppStore } from "@/store/useAppStore";
import { NewProjectButton } from "@/components/forms/NewProjectModal";

export function ContextSelector() {
  const { currentProjectId, currentGraphVersionId, currentTrafficScenarioId, setContext } = useAppStore();
  const { data: projects } = useQuery({ queryKey: ["projects"], queryFn: projectsApi.list });

  const currentProject = projects?.find((p) => p.id === currentProjectId) ?? projects?.[0];

  const { data: graphVersions } = useQuery({
    queryKey: ["graph-versions", currentProject?.id],
    queryFn: () => projectsApi.graphs(currentProject!.id),
    enabled: !!currentProject,
  });

  const { data: trafficScenarios } = useQuery({
    queryKey: ["traffic-scenarios", currentProject?.id],
    queryFn: () => trafficApi.list(currentProject!.id),
    enabled: !!currentProject,
  });

  // With real (multi-city) data, `projects` holds one entry per seeded
  // city -- default to the first returned project so every other page's
  // useAppStore((s) => s.currentProjectId) queries have something to work
  // with immediately, rather than staying null until a user manually
  // picks one from the (still-basic) trigger buttons below.
  //
  // Also guards against a stale id: `currentProjectId` is persisted to
  // localStorage, so after re-seeding (or switching databases) it can
  // point at a project that no longer exists -- the dropdown would show
  // the fallback project[0] while every page's queries kept using the
  // dead id underneath, 404ing. If the stored id isn't among the
  // fetched projects, reset it to project[0] instead of leaving it dangling.
  useEffect(() => {
    if (!projects || projects.length === 0) return;
    const stillExists = currentProjectId && projects.some((p) => p.id === currentProjectId);
    if (!stillExists) {
      setContext({ currentProjectId: projects[0].id, currentGraphVersionId: projects[0].default_graph_version_id ?? null, currentTrafficScenarioId: null });
    }
  }, [currentProjectId, projects, setContext]);

  // Same staleness guard for the graph version and traffic scenario: once
  // their own lists load, make sure the selected id still belongs to the
  // current project, defaulting to the newest of each.
  useEffect(() => {
    if (!graphVersions || graphVersions.length === 0) return;
    const stillExists = currentGraphVersionId && graphVersions.some((g) => g.id === currentGraphVersionId);
    if (!stillExists) {
      setContext({ currentGraphVersionId: graphVersions[0].id });
    }
  }, [currentGraphVersionId, graphVersions, setContext]);

  useEffect(() => {
    if (!trafficScenarios || trafficScenarios.length === 0) return;
    const stillExists = currentTrafficScenarioId && trafficScenarios.some((t) => t.id === currentTrafficScenarioId);
    if (!stillExists) {
      setContext({ currentTrafficScenarioId: trafficScenarios[0].id });
    }
  }, [currentTrafficScenarioId, trafficScenarios, setContext]);

  const currentGraphVersion = graphVersions?.find((g) => g.id === currentGraphVersionId) ?? graphVersions?.[0];
  const currentTrafficScenario = trafficScenarios?.find((t) => t.id === currentTrafficScenarioId) ?? trafficScenarios?.[0];

  return (
    <div className="flex items-center gap-1 text-sm">
      {/* Functional city/project switcher -- with multi_city_seed.py this
          lists one entry per seeded city (Ludhiana, Chandigarh, Delhi...).
          A styled Radix Select is a drop-in upgrade for the native <select>
          below once that dependency is added; this keeps the same
          onChange -> setContext wiring. */}
      <div className="relative flex items-center gap-1.5 rounded-md px-2.5 py-1.5 hover:bg-base-800 transition-colors">
        <span className="text-ink-500">Project</span>
        <select
          value={currentProject?.id ?? ""}
          onChange={(e) => {
            const project = projects?.find((p) => p.id === e.target.value);
            setContext({
              currentProjectId: e.target.value,
              currentGraphVersionId: project?.default_graph_version_id ?? null,
              currentTrafficScenarioId: null,
            });
          }}
          className="appearance-none bg-transparent font-medium text-ink-100 pr-4 outline-none cursor-pointer"
          aria-label="Select project"
        >
          {!projects?.length && <option value="">Select project</option>}
          {projects?.map((p) => (
            <option key={p.id} value={p.id} className="bg-base-900 text-ink-100">
              {p.name}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="text-ink-700 pointer-events-none absolute right-2" />
      </div>
      <NewProjectButton />
      <span className="text-ink-700">/</span>
      <div className="relative flex items-center gap-1.5 rounded-md px-2.5 py-1.5 hover:bg-base-800 transition-colors">
        <span className="text-ink-500">Network</span>
        <select
          value={currentGraphVersion?.id ?? ""}
          onChange={(e) => setContext({ currentGraphVersionId: e.target.value })}
          className="appearance-none bg-transparent font-medium text-ink-100 pr-4 outline-none cursor-pointer"
          aria-label="Select graph version"
          disabled={!graphVersions?.length}
        >
          {!graphVersions?.length && <option value="">—</option>}
          {graphVersions?.map((g) => (
            <option key={g.id} value={g.id} className="bg-base-900 text-ink-100">
              v{g.version_no}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="text-ink-700 pointer-events-none absolute right-2" />
      </div>
      <span className="text-ink-700">/</span>
      <div className="relative flex items-center gap-1.5 rounded-md px-2.5 py-1.5 hover:bg-base-800 transition-colors">
        <span className="text-ink-500">Traffic</span>
        <select
          value={currentTrafficScenario?.id ?? ""}
          onChange={(e) => setContext({ currentTrafficScenarioId: e.target.value })}
          className="appearance-none bg-transparent font-medium text-ink-100 pr-4 outline-none cursor-pointer"
          aria-label="Select traffic scenario"
          disabled={!trafficScenarios?.length}
        >
          {!trafficScenarios?.length && <option value="">—</option>}
          {trafficScenarios?.map((t) => (
            <option key={t.id} value={t.id} className="bg-base-900 text-ink-100">
              {t.name}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="text-ink-700 pointer-events-none absolute right-2" />
      </div>
    </div>
  );
}
