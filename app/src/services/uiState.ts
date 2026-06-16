import type { RouteId } from "../app/routes.js";

export type ShortcutAction = "regenerate" | "open-report" | "settings" | "focus-source-search";

export type ShortcutInput = {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  targetTagName?: string | null;
  targetIsContentEditable?: boolean;
};

export type UiState = {
  route: RouteId;
  selectedReportId: string;
  todayQuickSettingsOpen: boolean;
  settingsNetworkOpen: boolean;
  settingsAdvancedOpen: boolean;
};

export const uiStateStorageKey = "signalforge-ui-state";

export const defaultUiState: UiState = {
  route: "today",
  selectedReportId: "",
  todayQuickSettingsOpen: false,
  settingsNetworkOpen: false,
  settingsAdvancedOpen: false,
};

export function isRouteId(value: string): value is RouteId {
  return ["today", "reports", "sources", "settings", "setup"].includes(value);
}

export function loadUiState(storage: Storage | undefined = globalThis.localStorage): UiState {
  if (!storage) return defaultUiState;
  try {
    const raw = storage.getItem(uiStateStorageKey);
    if (!raw) return defaultUiState;
    return mergeUiState(defaultUiState, JSON.parse(raw) as Partial<UiState>);
  } catch {
    return defaultUiState;
  }
}

export function storeUiState(storage: Storage | undefined = globalThis.localStorage, state: UiState): void {
  storage?.setItem(uiStateStorageKey, JSON.stringify(mergeUiState(defaultUiState, state)));
}

export function mergeUiState(current: UiState, patch: Partial<UiState>): UiState {
  return {
    route: typeof patch.route === "string" && isRouteId(patch.route) ? patch.route : current.route,
    selectedReportId: typeof patch.selectedReportId === "string" ? patch.selectedReportId : current.selectedReportId,
    todayQuickSettingsOpen:
      typeof patch.todayQuickSettingsOpen === "boolean" ? patch.todayQuickSettingsOpen : current.todayQuickSettingsOpen,
    settingsNetworkOpen:
      typeof patch.settingsNetworkOpen === "boolean" ? patch.settingsNetworkOpen : current.settingsNetworkOpen,
    settingsAdvancedOpen:
      typeof patch.settingsAdvancedOpen === "boolean" ? patch.settingsAdvancedOpen : current.settingsAdvancedOpen,
  };
}

export function shortcutActionFromKey(input: ShortcutInput): ShortcutAction | null {
  if (isTypingTarget(input.targetTagName, input.targetIsContentEditable)) return null;
  const key = input.key.toLowerCase();
  const command = input.metaKey || input.ctrlKey;
  if (command && key === "r") return "regenerate";
  if (command && key === "o") return "open-report";
  if (command && key === ",") return "settings";
  if (!command && key === "/") return "focus-source-search";
  return null;
}

function isTypingTarget(tagName?: string | null, isContentEditable = false): boolean {
  if (isContentEditable) return true;
  if (!tagName) return false;
  return ["input", "textarea", "select"].includes(tagName.toLowerCase());
}
