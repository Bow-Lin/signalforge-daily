export type RouteId = "today" | "reports" | "sources" | "settings" | "setup";

export const primaryRoutes: Array<{ id: RouteId; label: string }> = [
  { id: "today", label: "今日" },
  { id: "reports", label: "报告" },
  { id: "sources", label: "信息源" },
  { id: "settings", label: "设置" },
];
