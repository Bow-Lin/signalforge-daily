import { primaryRoutes, type RouteId } from "../app/routes";
import type { ReactNode } from "react";

type Props = {
  route: RouteId;
  onRouteChange: (route: RouteId) => void;
  children: ReactNode;
};

export function AppShell({ route, onRouteChange, children }: Props) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">AI</span>
          <div>
            <strong>News Collection</strong>
            <span>Daily Digest</span>
          </div>
        </div>
        <nav>
          {primaryRoutes.map((item) => (
            <button
              key={item.id}
              className={route === item.id ? "nav-item active" : "nav-item"}
              onClick={() => onRouteChange(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
