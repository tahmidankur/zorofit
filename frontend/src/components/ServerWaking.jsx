import { useEffect, useState } from "react";
import { onServerWaking } from "../api.js";
import "./ServerWaking.css";

export default function ServerWaking() {
  const [waking, setWaking] = useState(false);

  useEffect(() => onServerWaking(setWaking), []);

  if (!waking) return null;
  return (
    <p className="server-waking small" role="status">
      Starting the server. This can take up to a minute on the free plan.
    </p>
  );
}
