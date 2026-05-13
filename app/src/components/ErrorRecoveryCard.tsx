import type { RunRecord } from "../types/run";

type Props = {
  run?: RunRecord;
  onRetry: () => void;
  onSettings: () => void;
  onOpenLogs: () => void;
};

export function ErrorRecoveryCard({ run, onRetry, onSettings, onOpenLogs }: Props) {
  if (!run?.error) return null;

  return (
    <section className="panel danger-panel">
      <div className="panel-header">
        <h2>摘要生成失败</h2>
        <span className="status failed">失败</span>
      </div>
      <h3>原因</h3>
      <p>{run.error.message}</p>
      <h3>可以尝试</h3>
      <ul className="fix-list">
        {run.error.suggestedActions.map((action) => (
          <li key={action}>{translateAction(action)}</li>
        ))}
      </ul>
      <div className="actions">
        <button onClick={onRetry}>重试</button>
        <button className="secondary" onClick={onSettings}>网络设置</button>
        <button className="secondary" onClick={onOpenLogs}>打开日志</button>
      </div>
    </section>
  );
}

function translateAction(action: string): string {
  const labels: Record<string, string> = {
    "Go to Settings and configure API key": "前往设置并配置 API Key",
    "Test connection before generating digest": "生成前先测试连接",
    "Check whether your proxy is running": "检查代理服务是否正在运行",
    "Switch proxy mode to No proxy": "将代理模式切换为不使用代理",
    "Update custom proxy address": "更新自定义代理地址",
    "Check internet connection": "检查网络连接",
    "Increase time range": "扩大摘要时间范围",
    "Retry later": "稍后重试",
    "Review the run log": "查看运行日志",
    "Test AI provider connection": "测试 AI 服务连接",
    "Check API key": "检查 API Key",
    "Change model": "更换模型",
    Retry: "重试",
    "Check workspace permissions": "检查工作区写入权限",
    "Choose another output folder": "选择其他输出文件夹",
    "Check API key and Base URL": "检查 API Key 和 Base URL",
    "Check Settings": "检查设置",
  };
  return labels[action] || action;
}
