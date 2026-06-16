import { useEffect, useMemo, useState } from "react";
import { SettingsForm } from "../components/SettingsForm";
import { PageHeader, type ToastItem } from "../components/ui";
import { copyText, getAppInfo, openLogsFolder, openPath } from "../services/bridge";
import type { AppInfo, AppSnapshot } from "../types/bridge";
import type { AppConfig } from "../types/config";
import type { UiState } from "../services/uiState";

type Props = {
  config: AppConfig;
  snapshot: AppSnapshot;
  onSaved: (snapshot: AppSnapshot) => void;
  demoMode?: boolean;
  onClearDemo?: () => void;
  uiState: UiState;
  onUiStateChange: (patch: Partial<UiState>) => void;
  onToast: (toast: Omit<ToastItem, "id">) => string;
};

export function SettingsPage({ config, snapshot, onSaved, demoMode = false, onClearDemo, uiState, onUiStateChange, onToast }: Props) {
  return (
    <div className="page">
      <PageHeader
        eyebrow="SETTINGS"
        title="本地配置"
        description="管理工作区、AI Provider、相关性偏好和摘要默认值。"
      />
      {demoMode ? (
        <section className="panel warning-panel">
          <div>
            <strong>当前是 Demo Mode</strong>
            <p className="muted">配置表单不会写入真实 workspace。清除 Demo 后可以设置自己的工作区和 API Key。</p>
          </div>
          <button className="secondary" onClick={onClearDemo}>清除 Demo 数据</button>
        </section>
      ) : (
        <SettingsForm config={config} onSaved={onSaved} uiState={uiState} onUiStateChange={onUiStateChange} onToast={onToast} />
      )}
      <AboutPanel config={config} snapshot={snapshot} demoMode={demoMode} />
    </div>
  );
}

function AboutPanel({ config, snapshot, demoMode }: { config: AppConfig; snapshot: AppSnapshot; demoMode: boolean }) {
  const [appInfo, setAppInfo] = useState<AppInfo | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getAppInfo().then(setAppInfo).catch(() => {
      setAppInfo({
        appName: "SignalForge Daily",
        version: "0.4.0",
        buildDate: "development",
        platform: navigator.platform || "unknown",
        workspacePath: undefined,
        repositoryUrl: "https://github.com/Bow-Lin/signalforge-daily",
        logsPath: undefined,
      });
    });
  }, []);

  const latestRun = snapshot.runs[0];
  const diagnostics = useMemo(() => {
    const lines = [
      `app: ${appInfo?.appName || "SignalForge Daily"}`,
      `version: ${appInfo?.version || "unknown"}`,
      `buildDate: ${appInfo?.buildDate || "unknown"}`,
      `platform: ${appInfo?.platform || "unknown"}`,
      `demoMode: ${demoMode ? "true" : "false"}`,
      `workspacePath: ${appInfo?.workspacePath || config.workspacePath || "not configured"}`,
      `automationEnabled: ${config.automation.enabled ? "true" : "false"}`,
      `lastRunStatus: ${latestRun?.status || "none"}`,
      `lastErrorType: ${latestRun?.error?.type || "none"}`,
      `sourceCount: ${config.sources.length}`,
      `reportCount: ${snapshot.reports.length}`,
      `logPath: ${appInfo?.logsPath || latestRun?.output?.logPath || "not configured"}`,
    ];
    return lines.join("\n");
  }, [appInfo, config, demoMode, latestRun, snapshot.reports.length]);

  const copyDiagnostics = async () => {
    await copyText(diagnostics);
    setMessage("诊断信息已复制。");
  };

  const openLogs = async () => {
    if (demoMode) {
      setMessage("Demo Mode 没有真实日志目录。");
      return;
    }
    try {
      await openLogsFolder();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <section className="panel about-panel">
      <div className="panel-header">
        <div>
          <h2>关于 SignalForge Daily</h2>
          <p className="muted">版本、工作区和诊断信息。诊断信息不会包含 API Key、token 或完整 secret config。</p>
        </div>
      </div>
      <div className="meta-grid about-grid">
        <Meta label="App name" value={appInfo?.appName || "SignalForge Daily"} />
        <Meta label="Version" value={appInfo?.version || "unknown"} />
        <Meta label="Build date" value={appInfo?.buildDate || "development"} />
        <Meta label="Platform" value={appInfo?.platform || navigator.platform || "unknown"} />
        <Meta label="Workspace" value={appInfo?.workspacePath || config.workspacePath || "未配置"} />
        <Meta label="Logs" value={appInfo?.logsPath || latestRun?.output?.logPath || "未配置"} />
      </div>
      <div className="actions">
        <button className="secondary" onClick={openLogs}>打开 logs folder</button>
        <button className="secondary" onClick={copyDiagnostics}>复制诊断信息</button>
        <button className="ghost-action" onClick={() => openPath(appInfo?.repositoryUrl || "https://github.com/Bow-Lin/signalforge-daily")}>打开 GitHub 仓库</button>
        <button className="ghost-action" onClick={() => openPath("https://github.com/Bow-Lin/signalforge-daily/releases")}>Open GitHub Releases</button>
      </div>
      {message && <p className="muted">{message}</p>}
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-item">
      <span>{label}</span>
      <strong title={value}>{value}</strong>
    </div>
  );
}
