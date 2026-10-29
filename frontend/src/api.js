import { getDeviceId } from "./device.js";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers);
  headers.set("X-Device-Id", getDeviceId());
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function getHealth() {
  return apiFetch("/api/health");
}
