import { SettingsForm } from "../components/SettingsForm";
import type { AppSnapshot } from "../types/bridge";
import type { AppConfig } from "../types/config";

type Props = {
  config: AppConfig;
  onSaved: (snapshot: AppSnapshot) => void;
};

export function SettingsPage({ config, onSaved }: Props) {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Settings</span>
          <h1>Local workspace and digest defaults</h1>
        </div>
      </header>
      <SettingsForm config={config} onSaved={onSaved} />
    </div>
  );
}
