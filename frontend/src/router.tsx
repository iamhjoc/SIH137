import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/shell/AppShell";
import { OverviewPage } from "@/pages/OverviewPage";
import { OperationsPage } from "@/pages/OperationsPage";
import { OptimizationPage } from "@/pages/OptimizationPage";
import { DirectionsPage } from "@/pages/DirectionsPage";
import { RoutesPage } from "@/pages/RoutesPage";
import { NetworkPage } from "@/pages/NetworkPage";
import { TrafficPage } from "@/pages/TrafficPage";
import { FleetPage } from "@/pages/FleetPage";
import { CustomersPage } from "@/pages/CustomersPage";
import { BenchmarksPage } from "@/pages/BenchmarksPage";
import { ExperimentsPage } from "@/pages/ExperimentsPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { AdminPage } from "@/pages/AdminPage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <OverviewPage /> },
      { path: "/operations", element: <OperationsPage /> },
      { path: "/optimization", element: <OptimizationPage /> },
      { path: "/directions", element: <DirectionsPage /> },
      { path: "/routes", element: <RoutesPage /> },
      { path: "/routes/:jobId", element: <RoutesPage /> },
      { path: "/network", element: <NetworkPage /> },
      { path: "/traffic", element: <TrafficPage /> },
      { path: "/fleet", element: <FleetPage /> },
      { path: "/customers", element: <CustomersPage /> },
      { path: "/benchmarks", element: <BenchmarksPage /> },
      { path: "/experiments", element: <ExperimentsPage /> },
      { path: "/history", element: <HistoryPage /> },
      { path: "/admin", element: <AdminPage /> },
    ],
  },
]);
