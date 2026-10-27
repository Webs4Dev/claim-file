import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

const ICONS = { error: AlertCircle, warning: AlertTriangle, success: CheckCircle2 };

/** variant: "info" (default) | "success" | "warning" | "error" | "demo"; colours in DESIGN.md */
export default function Notice({ variant = "info", children }) {
  const Icon = ICONS[variant] || Info;
  return (
    <div className={`notice notice-${variant}`} role={variant === "error" ? "alert" : "status"}>
      <Icon size={16} aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
