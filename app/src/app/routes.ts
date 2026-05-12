export type RouteId = "today" | "reports" | "settings" | "setup";

export const primaryRoutes: Array<{ id: RouteId; label: string }> = [
  { id: "today", label: "Today" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];
