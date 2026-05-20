import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/AppShell";
import { ReportsPage } from "../pages/ReportsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { SetupPage } from "../pages/SetupPage";
import { SourcesPage } from "../pages/SourcesPage";
import { TodayPage } from "../pages/TodayPage";
import { getConfigReadiness } from "../services/configReadiness";
import { getSnapshot, onAppNavigate, onAutomationChanged, onAutomationNotify, onDigestEvent } from "../services/bridge";
import type { AppSnapshot } from "../types/bridge";
import type { GenerateDigestEvent, RunRecord } from "../types/run";
import { notify, registerNotificationOpenHandler } from "../services/notificationService";
import type { RouteId } from "./routes";

export function App() {
  const [route, setRoute] = useState<RouteId>("today");
  const [snapshot, setSnapshot] = useState<AppSnapshot>({ config: null, runs: [], reports: [], sourceStats: [], feedback: [] });
  const [loading, setLoading] = useState(true);
  const [runLogs, setRunLogs] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState("");

  const refresh = async () => {
    const next = await getSnapshot();
    setSnapshot(next);
    if (!getConfigReadiness(next.config).ready) setRoute("setup");
    return next;
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
    const unlistenDigest = onDigestEvent((event) => {
      handleDigestEvent(event);
    });
    const unlistenNavigate = onAppNavigate((nextRoute) => {
      if (["today", "reports", "sources", "settings"].includes(nextRoute)) {
        setRoute(nextRoute as RouteId);
      }
    });
    const unlistenAutomation = onAutomationChanged(() => {
      refresh();
    });
    const unlistenNotify = onAutomationNotify((payload) => {
      notify(payload.title, payload.body);
    });
    let unlistenNotificationAction: (() => void) | null = null;
    registerNotificationOpenHandler(() => {
      setRoute("today");
    }).then((handler) => {
      unlistenNotificationAction = handler;
    });
    return () => {
      unlistenDigest();
      unlistenNavigate();
      unlistenAutomation();
      unlistenNotify();
      unlistenNotificationAction?.();
    };
  }, []);

  const handleDigestEvent = (event: GenerateDigestEvent) => {
    if (event.type === "log") {
      setRunLogs((items) => [...items.slice(-99), event.message]);
      return;
    }
    if (event.type === "progress") {
      setCurrentStep(event.step);
      return;
    }
    if (event.type === "started" || event.type === "completed" || event.type === "failed") {
      setSnapshot((current) => upsertRun(current, event.record));
      if (event.type === "started") setRunLogs([]);
      if (event.type !== "started") {
        refresh();
      }
    }
  };

  const latestRun = useMemo(() => snapshot.runs[0], [snapshot.runs]);
  const runningRun = useMemo(() => snapshot.runs.find((run) => run.status === "running"), [snapshot.runs]);
  const configReadiness = useMemo(() => getConfigReadiness(snapshot.config), [snapshot.config]);

  if (loading) {
    return <div className="boot">正在读取本地工作区...</div>;
  }

  if (route === "setup" || !configReadiness.ready || !snapshot.config) {
    return <SetupPage snapshot={snapshot} onReady={(next) => { setSnapshot(next); setRoute(getConfigReadiness(next.config).ready ? "today" : "setup"); }} />;
  }

  return (
    <AppShell route={route} onRouteChange={setRoute}>
      {route === "today" && (
        <TodayPage
          config={snapshot.config}
          latestRun={latestRun}
          latestReport={snapshot.reports[0]}
          runningRun={runningRun}
          runLogs={runLogs}
          currentStep={currentStep}
          onNavigate={setRoute}
          onSnapshot={setSnapshot}
        />
      )}
      {route === "reports" && <ReportsPage reports={snapshot.reports} onSnapshot={setSnapshot} />}
      {route === "sources" && <SourcesPage config={snapshot.config} sourceStats={snapshot.sourceStats} onSnapshot={setSnapshot} />}
      {route === "settings" && <SettingsPage config={snapshot.config} onSaved={setSnapshot} />}
    </AppShell>
  );
}

function upsertRun(snapshot: AppSnapshot, run: RunRecord): AppSnapshot {
  const remaining = snapshot.runs.filter((item) => item.id !== run.id);
  return {
    ...snapshot,
    runs: [run, ...remaining].sort((a, b) => b.startedAt.localeCompare(a.startedAt)),
  };
}
