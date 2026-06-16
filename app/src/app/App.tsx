import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/AppShell";
import { ReportsPage } from "../pages/ReportsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { SetupPage } from "../pages/SetupPage";
import { SourcesPage } from "../pages/SourcesPage";
import { TodayPage } from "../pages/TodayPage";
import { ToastHost, type ToastItem } from "../components/ui";
import { sampleSnapshot } from "../demo/sampleData";
import { getConfigReadiness } from "../services/configReadiness";
import { generateDigest, getSnapshot, onAppNavigate, onAutomationChanged, onAutomationNotify, onDigestEvent } from "../services/bridge";
import { loadUiState, mergeUiState, shortcutActionFromKey, storeUiState, type UiState } from "../services/uiState";
import type { AppSnapshot } from "../types/bridge";
import type { GenerateDigestEvent, RunRecord } from "../types/run";
import { notify, registerNotificationOpenHandler } from "../services/notificationService";
import type { RouteId } from "./routes";

export function App() {
  const [uiState, setUiState] = useState<UiState>(() => loadUiState());
  const [route, setRouteValue] = useState<RouteId>(() => uiState.route);
  const [snapshot, setSnapshot] = useState<AppSnapshot>({ config: null, runs: [], reports: [], sourceStats: [], feedback: [] });
  const [demoMode, setDemoMode] = useState(() => localStorage.getItem("signalforge-demo-mode") === "true");
  const [loading, setLoading] = useState(true);
  const [runLogs, setRunLogs] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState("");
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [todayFocusRequest, setTodayFocusRequest] = useState<{ target: "latest" | "error"; nonce: number } | null>(null);
  const [sourceSearchFocusNonce, setSourceSearchFocusNonce] = useState(0);

  const updateUiState = (patch: Partial<UiState>) => {
    setUiState((current) => {
      const next = mergeUiState(current, patch);
      storeUiState(localStorage, next);
      return next;
    });
  };

  const setRoute = (nextRoute: RouteId) => {
    setRouteValue(nextRoute);
    updateUiState({ route: nextRoute });
  };

  const dismissToast = (id: string) => {
    setToasts((items) => items.filter((item) => item.id !== id));
  };

  const showToast = (toast: Omit<ToastItem, "id">) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((items) => [{ id, ...toast }, ...items].slice(0, 3));
    window.setTimeout(() => dismissToast(id), 7000);
    return id;
  };

  const refresh = async () => {
    if (demoMode) {
      const demo = cloneSnapshot(sampleSnapshot);
      setSnapshot(demo);
      return demo;
    }
    const next = await getSnapshot();
    setSnapshot(next);
    if (!getConfigReadiness(next.config).ready) setRoute("setup");
    return next;
  };

  const latestRun = useMemo(() => snapshot.runs[0], [snapshot.runs]);
  const runningRun = useMemo(() => snapshot.runs.find((run) => run.status === "running"), [snapshot.runs]);
  const latestReport = useMemo(() => snapshot.reports[0], [snapshot.reports]);
  const configReadiness = useMemo(() => getConfigReadiness(snapshot.config), [snapshot.config]);

  useEffect(() => {
    if (demoMode) {
      setSnapshot(cloneSnapshot(sampleSnapshot));
      setRoute("today");
      setLoading(false);
    } else {
      refresh().finally(() => setLoading(false));
    }
    const unlistenDigest = onDigestEvent((event) => {
      if (!demoMode) handleDigestEvent(event);
    });
    const unlistenNavigate = onAppNavigate((nextRoute) => {
      if (["today", "reports", "sources", "settings"].includes(nextRoute)) {
        setRoute(nextRoute as RouteId);
      }
    });
    const unlistenAutomation = onAutomationChanged(() => {
      if (!demoMode) refresh();
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
  }, [demoMode]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const action = shortcutActionFromKey({
        key: event.key,
        metaKey: event.metaKey,
        ctrlKey: event.ctrlKey,
        targetTagName: target?.tagName,
        targetIsContentEditable: target?.isContentEditable,
      });
      if (!action) return;
      event.preventDefault();
      if (action === "settings") {
        setRoute("settings");
        return;
      }
      if (action === "open-report") {
        if (latestReport || latestRun?.output?.markdownPath) setRoute("reports");
        return;
      }
      if (action === "focus-source-search") {
        setRoute("sources");
        setSourceSearchFocusNonce((value) => value + 1);
        return;
      }
      if (action === "regenerate" && !demoMode && configReadiness.ready && !runningRun) {
        void generateDigest();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [configReadiness.ready, demoMode, latestReport, latestRun?.output?.markdownPath, runningRun]);

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
        if (event.record.trigger === "manual") {
          setRoute("today");
          setTodayFocusRequest({ target: event.type === "completed" ? "latest" : "error", nonce: Date.now() });
          showToast(
            event.type === "completed"
              ? {
                  title: "已生成今日摘要",
                  description: "最新精选已放在 Today 顶部。",
                  actionLabel: "查看完整报告",
                  onAction: () => setRoute("reports"),
                }
              : {
                  title: "生成失败",
                  description: "已定位到修复建议，可以直接重试或打开日志。",
                  actionLabel: "查看修复建议",
                  onAction: () => setTodayFocusRequest({ target: "error", nonce: Date.now() }),
                },
          );
        }
      }
    }
  };

  const enterDemoMode = () => {
    localStorage.setItem("signalforge-demo-mode", "true");
    setDemoMode(true);
    setSnapshot(cloneSnapshot(sampleSnapshot));
    setRoute("today");
  };

  const clearDemoMode = async () => {
    localStorage.removeItem("signalforge-demo-mode");
    setDemoMode(false);
    setLoading(true);
    const next = await getSnapshot();
    setSnapshot(next);
    setRoute(getConfigReadiness(next.config).ready ? "today" : "setup");
    setLoading(false);
  };

  if (loading) {
    return <div className="boot">正在读取本地工作区...</div>;
  }

  if (!demoMode && (route === "setup" || !configReadiness.ready || !snapshot.config)) {
    return <SetupPage snapshot={snapshot} onDemo={enterDemoMode} onReady={(next) => { setSnapshot(next); setRoute(getConfigReadiness(next.config).ready ? "today" : "setup"); }} />;
  }

  return (
    <AppShell route={route} onRouteChange={setRoute}>
      {demoMode && (
        <section className="demo-banner">
          <div>
            <strong>Demo Mode</strong>
            <span>当前展示的是内置样例数据，不会调用 AI Provider，也不会写入真实 workspace。</span>
          </div>
          <button className="secondary small-button" onClick={clearDemoMode}>清除 Demo 数据</button>
        </section>
      )}
      {route === "today" && (
        <TodayPage
          config={snapshot.config || sampleSnapshot.config!}
          latestRun={latestRun}
          latestReport={latestReport}
          runningRun={runningRun}
          runLogs={runLogs}
          currentStep={currentStep}
          onNavigate={setRoute}
          onSnapshot={setSnapshot}
          demoMode={demoMode}
          uiState={uiState}
          onUiStateChange={updateUiState}
          focusRequest={todayFocusRequest}
          onToast={showToast}
          itemFeedback={snapshot.feedback}
        />
      )}
      {route === "reports" && (
        <ReportsPage
          reports={snapshot.reports}
          onSnapshot={setSnapshot}
          uiState={uiState}
          onUiStateChange={updateUiState}
          onToast={showToast}
        />
      )}
      {route === "sources" && (
        <SourcesPage
          config={snapshot.config || sampleSnapshot.config!}
          sourceStats={snapshot.sourceStats}
          onSnapshot={setSnapshot}
          demoMode={demoMode}
          searchFocusNonce={sourceSearchFocusNonce}
          onToast={showToast}
        />
      )}
      {route === "settings" && (
        <SettingsPage
          config={snapshot.config || sampleSnapshot.config!}
          snapshot={snapshot}
          onSaved={setSnapshot}
          demoMode={demoMode}
          onClearDemo={clearDemoMode}
          uiState={uiState}
          onUiStateChange={updateUiState}
          onToast={showToast}
        />
      )}
      <ToastHost toasts={toasts} onDismiss={dismissToast} />
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

function cloneSnapshot(snapshot: AppSnapshot): AppSnapshot {
  return JSON.parse(JSON.stringify(snapshot)) as AppSnapshot;
}
