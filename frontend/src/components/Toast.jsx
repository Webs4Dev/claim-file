import { useEffect } from "react";
import { CheckCircle2 } from "lucide-react";

export default function Toast({ message, onDone }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(onDone, 3500);
    return () => clearTimeout(timer);
  }, [message, onDone]);

  if (!message) return null;
  return (
    <div className="toast" role="status">
      <CheckCircle2 size={17} aria-hidden="true" />
      {message}
    </div>
  );
}
