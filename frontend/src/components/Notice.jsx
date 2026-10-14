import { AlertCircle, Info } from "lucide-react";

/** variant: "error" | "demo" | "info" */
export default function Notice({ variant = "info", children }) {
  const Icon = variant === "error" ? AlertCircle : Info;
  return (
    <div className={`notice notice-${variant}`} role={variant === "error" ? "alert" : "status"}>
      <Icon size={16} aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
