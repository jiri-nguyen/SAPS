import { useEffect, useState } from "react";

import { type ApiHealth, fetchApiHealth } from "./api/health";

export function App({ checkHealth = fetchApiHealth }: { checkHealth?: () => Promise<ApiHealth> }) {
  const [health, setHealth] = useState<ApiHealth | "checking">("checking");

  useEffect(() => {
    let active = true;
    void checkHealth().then((result) => {
      if (active) setHealth(result);
    });
    return () => {
      active = false;
    };
  }, [checkHealth]);

  return (
    <main>
      <h1>Smart-AP-Suite</h1>
      <p>
        SAPS API: <strong data-testid="api-health">{health}</strong>
      </p>
    </main>
  );
}
