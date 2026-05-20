import { isPermissionGranted, onAction, registerActionTypes, requestPermission, sendNotification } from "@tauri-apps/plugin-notification";

export type NotificationPermissionState = "granted" | "denied" | "prompt" | "unsupported";

export async function getNotificationPermission(): Promise<NotificationPermissionState> {
  try {
    return (await isPermissionGranted()) ? "granted" : "prompt";
  } catch {
    return "unsupported";
  }
}

export async function ensureNotificationPermission(): Promise<NotificationPermissionState> {
  try {
    if (await isPermissionGranted()) return "granted";
    const permission = await requestPermission();
    return permission === "granted" ? "granted" : permission === "denied" ? "denied" : "prompt";
  } catch {
    return "unsupported";
  }
}

export async function notify(title: string, body: string): Promise<boolean> {
  const permission = await ensureNotificationPermission();
  if (permission !== "granted") return false;
  try {
    await registerDigestNotificationAction();
    sendNotification({ title, body, actionTypeId: "digest-open", autoCancel: true, extra: { route: "today" } });
    return true;
  } catch {
    return false;
  }
}

export async function registerNotificationOpenHandler(listener: () => void): Promise<() => void> {
  await registerDigestNotificationAction();
  const handler = await onAction(() => listener());
  return () => handler.unregister();
}

let actionRegistered = false;

async function registerDigestNotificationAction(): Promise<void> {
  if (actionRegistered) return;
  await registerActionTypes([
    {
      id: "digest-open",
      actions: [{ id: "open", title: "打开 SignalForge Daily", foreground: true }],
    },
  ]);
  actionRegistered = true;
}
