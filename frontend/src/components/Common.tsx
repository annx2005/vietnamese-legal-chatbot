import { FileText, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";

export function Metric({
  label,
  value,
  tone = "neutral"
}: {
  label: string;
  value: number;
  tone?: "neutral" | "ok" | "warn" | "bad";
}) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
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
  const icon =
    status === "failed" ? (
      <AlertTriangle size={14} />
    ) : status === "done" ? (
      <CheckCircle2 size={14} />
    ) : (
      <Loader2 className="spin" size={14} />
    );
  return (
    <span className={`badge ${status}`}>
      {icon}
      {status}
    </span>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty">
      <FileText size={22} />
      <span>{text}</span>
    </div>
  );
}
