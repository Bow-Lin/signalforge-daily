import { SettingsForm } from "../components/SettingsForm";
import { PageHeader } from "../components/ui";
import type { AppSnapshot } from "../types/bridge";
import type { AppConfig } from "../types/config";

type Props = {
  config: AppConfig;
  onSaved: (snapshot: AppSnapshot) => void;
};

export function SettingsPage({ config, onSaved }: Props) {
  return (
    <div className="page">
      <PageHeader
        eyebrow="SETTINGS"
        title="本地配置"
        description="管理工作区、AI Provider、相关性偏好和摘要默认值。"
      />
      <SettingsForm config={config} onSaved={onSaved} />
    </div>
  );
}
