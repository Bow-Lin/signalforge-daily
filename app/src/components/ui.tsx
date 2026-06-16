import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p className="page-subtitle">{description}</p>}
      </div>
      {actions && <div className="header-actions">{actions}</div>}
    </header>
  );
}

type StatusBadgeProps = {
  children: ReactNode;
  tone?: "neutral" | "success" | "running" | "failed" | "warning" | "disabled" | "healthy" | "noisy";
};

export function StatusBadge({ children, tone = "neutral" }: StatusBadgeProps) {
  return <span className={`status-badge ${tone}`}>{children}</span>;
}

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <section className="panel empty-state">
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </section>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <section className="panel loading-state">
      <span className="loading-dot" />
      <span>{label}</span>
    </section>
  );
}

export function ErrorState({ title, description, action }: EmptyStateProps) {
  return (
    <section className="panel error-state">
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </section>
  );
}

export type ToastItem = {
  id: string;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function ToastHost({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: string) => void }) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-host" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div className="toast" key={toast.id}>
          <div>
            <strong>{toast.title}</strong>
            {toast.description && <span>{toast.description}</span>}
          </div>
          <div className="toast-actions">
            {toast.actionLabel && toast.onAction && (
              <button className="ghost-action small-button" onClick={toast.onAction}>
                {toast.actionLabel}
              </button>
            )}
            <button className="secondary small-button" onClick={() => onDismiss(toast.id)} aria-label="关闭提示">
              关闭
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
