import { SettingsForm } from "../components/SettingsForm";
import type { AppSnapshot } from "../types/bridge";

type Props = {
  snapshot: AppSnapshot;
  onReady: (snapshot: AppSnapshot) => void;
};

export function SetupPage({ snapshot, onReady }: Props) {
  return (
    <main className="setup">
      <section className="setup-copy">
        <span className="eyebrow">Welcome</span>
        <h1>3 分钟生成第一份日报。</h1>
        <p>SignalForge Daily 会把配置、报告、日志和运行历史都放在你选择的本地工作区。完成连接测试后，就可以进入 Today 一键生成。</p>
        <ol className="setup-steps">
          <li><strong>选择 Workspace</strong><span>用于保存 app-config.json、reports、runs 和 logs。</span></li>
          <li><strong>配置 AI Provider</strong><span>填写 API Key、Base URL 和 Model。</span></li>
          <li><strong>Test Connection</strong><span>确认模型服务可用，再进入 Today。</span></li>
          <li><strong>生成 Daily Digest</strong><span>在 Today 点击一次即可运行现有 digest CLI。</span></li>
        </ol>
      </section>
      <section className="setup-form">
        <SettingsForm config={snapshot.config} onSaved={onReady} compact />
      </section>
    </main>
  );
}
