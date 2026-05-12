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
        <span className="eyebrow">Welcome Setup</span>
        <h1>Generate your first AI digest in three minutes.</h1>
        <p>Choose a local workspace, configure your AI provider, test the settings, then generate today's technical digest.</p>
        <ol>
          <li>Choose workspace folder</li>
          <li>Configure AI provider</li>
          <li>Test connection</li>
          <li>Choose default language</li>
          <li>Generate first digest</li>
        </ol>
      </section>
      <section className="setup-form">
        <SettingsForm config={snapshot.config} onSaved={onReady} compact />
      </section>
    </main>
  );
}
