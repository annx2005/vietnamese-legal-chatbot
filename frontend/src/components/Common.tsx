import type { ReactNode } from "react";
import { FileText, AlertTriangle, CheckCircle2, Loader2, Clock } from "lucide-react";

export function Metric({
  label,
  value,
  tone = "neutral",
  icon,
  helper
}: {
  label: string;
  value: number;
  tone?: "neutral" | "ok" | "warn" | "bad";
  icon?: ReactNode;
  helper?: string;
}) {
  return (
    <div className={`metric ${tone}`}>
      <div className="metric-topline">
        <div>
          <span>{label}</span>
          {helper && <small>{helper}</small>}
        </div>
        {icon && <div className="metric-icon">{icon}</div>}
      </div>
      <strong>{value}</strong>
    </div>
  );
}

export function PanelTitle({ title }: { title: string; onRefresh?: () => void }) {
  return (
    <div className="panel-title">
      <h2>{title}</h2>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const isFailed = normalized === "failed" || normalized === "error";
  const isDone = normalized === "done" || normalized === "completed" || normalized === "success";
  const icon = isFailed ? (
    <AlertTriangle size={14} />
  ) : isDone ? (
    <CheckCircle2 size={14} />
  ) : normalized === "pending" ? (
    <Clock size={14} />
  ) : (
    <Loader2 className="spin" size={14} />
  );

  return (
    <span className={`badge ${normalized}`}>
      {icon}
      {status}
    </span>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty">
      <div className="empty-icon" aria-hidden="true">
        <FileText size={22} />
      </div>
      <span>{text}</span>
    </div>
  );
}
