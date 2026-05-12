import { useState } from "react";
import { chooseFolder, saveConfig, testConnection } from "../services/bridge";
import type { AppSnapshot } from "../types/bridge";
import { defaultConfig, type AppConfig } from "../types/config";

type Props = {
  config: AppConfig | null;
  onSaved: (snapshot: AppSnapshot) => void;
  compact?: boolean;
};

export function SettingsForm({ config, onSaved, compact = false }: Props) {
  const [draft, setDraft] = useState<AppConfig>(config || defaultConfig());
  const [showKey, setShowKey] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [testMessage, setTestMessage] = useState("");
  const [testing, setTesting] = useState(false);

  const update = <T extends keyof AppConfig>(section: T, value: Partial<AppConfig[T]>) => {
    setDraft((current) => ({
      ...current,
      [section]: { ...(current[section] as object), ...value },
    }));
  };

  const pickWorkspace = async () => {
    const folder = await chooseFolder();
    if (!folder) return;
    setDraft((current) => ({
      ...current,
      workspacePath: folder,
      outputPath: current.outputPath || `${folder}/reports`,
    }));
  };

  const save = async () => {
    try {
      const next = await saveConfig(draft);
      setMessage("Settings saved.");
      onSaved(next);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const test = async () => {
    setTesting(true);
    setTestMessage("");
    try {
      const result = await testConnection(draft);
      setTestMessage(result.message);
    } catch (err) {
      setTestMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="settings-form">
      <section className="panel">
        <h2>Workspace</h2>
        <label>
          Workspace folder
          <div className="inline-field">
            <input value={draft.workspacePath} onChange={(event) => setDraft({ ...draft, workspacePath: event.target.value })} />
            <button className="secondary" onClick={pickWorkspace}>Choose</button>
          </div>
        </label>
        <label>
          Output folder
          <input value={draft.outputPath} onChange={(event) => setDraft({ ...draft, outputPath: event.target.value })} />
        </label>
      </section>

      <section className="panel">
        <h2>AI Provider</h2>
        <label>
          Provider type
          <select value={draft.aiProvider.provider} onChange={(event) => update("aiProvider", { provider: event.target.value as AppConfig["aiProvider"]["provider"] })}>
            <option value="iflow">iFlow</option>
            <option value="openai_compatible">OpenAI compatible</option>
            <option value="custom">Custom</option>
          </select>
        </label>
        <label>
          API key
          <div className="inline-field">
            <input
              type={showKey ? "text" : "password"}
              value={draft.aiProvider.apiKey}
              onChange={(event) => update("aiProvider", { apiKey: event.target.value })}
            />
            <button className="secondary" onClick={() => setShowKey((value) => !value)}>{showKey ? "Hide" : "Show"}</button>
          </div>
        </label>
        <label>
          Base URL
          <input value={draft.aiProvider.baseUrl || ""} onChange={(event) => update("aiProvider", { baseUrl: event.target.value })} />
        </label>
        <label>
          Model
          <input value={draft.aiProvider.model} onChange={(event) => update("aiProvider", { model: event.target.value })} />
        </label>
        <div className="actions">
          <button className="secondary" onClick={test} disabled={testing}>{testing ? "Testing..." : "Test connection"}</button>
          {testMessage && <span className={testMessage.includes("passed") || testMessage.includes("成功") ? "status success" : testMessage.includes("failed") || testMessage.includes("not configured") || testMessage.includes("is not") ? "status failed" : "muted"}>{testMessage}</span>}
        </div>
      </section>

      <section className="panel">
        <h2>Digest Defaults</h2>
        <div className="field-grid">
          <label>
            Default language
            <select value={draft.digestDefaults.language} onChange={(event) => update("digestDefaults", { language: event.target.value as AppConfig["digestDefaults"]["language"] })}>
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </label>
          <label>
            Default time range
            <select value={draft.digestDefaults.timeRangeHours} onChange={(event) => update("digestDefaults", { timeRangeHours: Number(event.target.value) })}>
              <option value={24}>24h</option>
              <option value={48}>48h</option>
              <option value={72}>72h</option>
              <option value={168}>7d</option>
            </select>
          </label>
          <label>
            Default Top N
            <input type="number" min={1} max={50} value={draft.digestDefaults.topN} onChange={(event) => update("digestDefaults", { topN: Number(event.target.value) })} />
          </label>
        </div>
      </section>

      <section className="panel">
        <h2>Network</h2>
        <label>
          Proxy mode
          <select value={draft.network.proxyMode} onChange={(event) => update("network", { proxyMode: event.target.value as AppConfig["network"]["proxyMode"] })}>
            <option value="system">Use system proxy</option>
            <option value="none">No proxy</option>
            <option value="custom">Custom proxy</option>
          </select>
        </label>
        {draft.network.proxyMode === "custom" && (
          <div className="field-grid">
            <label>
              HTTP proxy
              <input value={draft.network.httpProxy || ""} onChange={(event) => update("network", { httpProxy: event.target.value })} />
            </label>
            <label>
              HTTPS proxy
              <input value={draft.network.httpsProxy || ""} onChange={(event) => update("network", { httpsProxy: event.target.value })} />
            </label>
          </div>
        )}
      </section>

      {!compact && (
        <section className="panel">
          <button className="fold" onClick={() => setAdvancedOpen((value) => !value)}>
            Advanced {advancedOpen ? "▲" : "▼"}
          </button>
          {advancedOpen && (
            <div className="field-grid">
              <label>
                Feed concurrency
                <input type="number" min={1} value={draft.advanced.feedConcurrency || 10} onChange={(event) => update("advanced", { feedConcurrency: Number(event.target.value) })} />
              </label>
              <label>
                AI retries
                <input type="number" min={0} value={draft.advanced.aiRetries || 1} onChange={(event) => update("advanced", { aiRetries: Number(event.target.value) })} />
              </label>
              <label>
                Max AI articles
                <input type="number" min={1} value={draft.advanced.maxAiArticles || 120} onChange={(event) => update("advanced", { maxAiArticles: Number(event.target.value) })} />
              </label>
            </div>
          )}
        </section>
      )}

      <div className="sticky-actions">
        {message && <span>{message}</span>}
        <button onClick={save} disabled={!draft.workspacePath}>Save Settings</button>
      </div>
    </div>
  );
}
