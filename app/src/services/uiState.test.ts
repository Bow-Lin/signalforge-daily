import { test } from "node:test";
import { strict as assert } from "node:assert";
import {
  defaultUiState,
  isRouteId,
  loadUiState,
  mergeUiState,
  shortcutActionFromKey,
  storeUiState,
  type UiState,
} from "./uiState.js";

class MemoryStorage implements Storage {
  private values = new Map<string, string>();

  get length(): number {
    return this.values.size;
  }

  clear(): void {
    this.values.clear();
  }

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  key(index: number): string | null {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

test("loads defaults when stored UI state is missing or invalid", () => {
  const storage = new MemoryStorage();

  assert.deepEqual(loadUiState(storage), defaultUiState);

  storage.setItem("signalforge-ui-state", "{bad json");
  assert.deepEqual(loadUiState(storage), defaultUiState);
});

test("stores and merges only supported page state", () => {
  const storage = new MemoryStorage();
  const next: UiState = mergeUiState(defaultUiState, {
    route: "reports",
    selectedReportId: "report-1",
    todayQuickSettingsOpen: true,
    settingsAdvancedOpen: true,
    settingsNetworkOpen: true,
  });

  storeUiState(storage, next);

  assert.deepEqual(loadUiState(storage), next);
  assert.equal(isRouteId("sources"), true);
  assert.equal(isRouteId("unknown"), false);
});

test("maps supported keyboard shortcuts and ignores typing targets", () => {
  assert.equal(shortcutActionFromKey({ key: "r", metaKey: false, ctrlKey: true }), "regenerate");
  assert.equal(shortcutActionFromKey({ key: "o", metaKey: true, ctrlKey: false }), "open-report");
  assert.equal(shortcutActionFromKey({ key: ",", metaKey: false, ctrlKey: true }), "settings");
  assert.equal(shortcutActionFromKey({ key: "/", metaKey: false, ctrlKey: false }), "focus-source-search");
  assert.equal(shortcutActionFromKey({ key: "/", metaKey: false, ctrlKey: false, targetTagName: "input" }), null);
  assert.equal(shortcutActionFromKey({ key: "r", metaKey: false, ctrlKey: false }), null);
});
