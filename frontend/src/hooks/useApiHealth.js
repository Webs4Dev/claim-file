import { useCallback, useEffect, useState } from "react";
import { checkHealth } from "../api";

/** null = checking, true = reachable, false = unreachable. Re-checks every 30s. */
export default function useApiHealth() {
  const [healthy, setHealthy] = useState(null);

  const check = useCallback(async () => {
    try {
      await checkHealth();
      setHealthy(true);
    } catch {
      setHealthy(false);
    }
  }, []);

  useEffect(() => {
    check();
    const timer = setInterval(check, 30000);
    return () => clearInterval(timer);
  }, [check]);

  return { healthy, recheck: check };
}
