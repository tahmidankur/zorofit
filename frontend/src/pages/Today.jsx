import { useEffect, useState } from "react";
import { getHealth } from "../api.js";

function ServerStatus() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    getHealth()
      .then((data) => setStatus(data.ok ? "ok" : "down"))
      .catch(() => setStatus("down"));
  }, []);

  const text = {
    checking: "Checking the server…",
    ok: "Server is running.",
    down: "Can't reach the server.",
  }[status];

  return (
    <p className="muted" role="status">
      {text}
    </p>
  );
}

export default function Today() {
  return (
    <section>
      <h1 className="page-title">Today</h1>
      <div className="card">
        <p>Calories, protein, and today's workout will show here.</p>
      </div>
      <div style={{ marginTop: 16 }}>
        <ServerStatus />
      </div>
    </section>
  );
}
