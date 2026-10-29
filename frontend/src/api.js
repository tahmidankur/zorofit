import { getDeviceId } from "./device.js";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function browserTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    const field = first.loc?.[first.loc.length - 1];
    return field ? `${field}: ${first.msg}` : first.msg;
  }
  return `Request failed (${status})`;
}

// The free API host sleeps when idle; a slow first response means it is waking up.
const SLOW_START_MS = 3000;
let serverAwake = false;
const wakeListeners = new Set();

export function onServerWaking(listener) {
  wakeListeners.add(listener);
  return () => wakeListeners.delete(listener);
}

function notifyWaking(waking) {
  wakeListeners.forEach((listener) => listener(waking));
}

export async function apiFetch(path, { method = "GET", body } = {}) {
  const headers = {
    "X-Device-Id": getDeviceId(),
    "X-Timezone": browserTimezone(),
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const timer = serverAwake ? null : setTimeout(() => notifyWaking(true), SLOW_START_MS);
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } finally {
    clearTimeout(timer);
  }
  if (!serverAwake) {
    serverAwake = true;
    notifyWaking(false);
  }
  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(data, response.status));
  }
  return data;
}

export const api = {
  health: () => apiFetch("/api/health"),
  loadDemoData: () => apiFetch("/api/demo", { method: "POST" }),
  getProfile: () => apiFetch("/api/profile"),
  saveProfile: (profile) => apiFetch("/api/profile", { method: "PUT", body: profile }),
  getToday: () => apiFetch("/api/today"),
  listMeals: () => apiFetch("/api/meals"),
  createMeal: (meal) => apiFetch("/api/meals", { method: "POST", body: meal }),
  updateMeal: (id, meal) => apiFetch(`/api/meals/${id}`, { method: "PUT", body: meal }),
  deleteMeal: (id) => apiFetch(`/api/meals/${id}`, { method: "DELETE" }),
  searchFoods: (query) => apiFetch(`/api/foods/search?q=${encodeURIComponent(query)}`),
  listCustomFoods: () => apiFetch("/api/foods/custom"),
  createCustomFood: (food) => apiFetch("/api/foods/custom", { method: "POST", body: food }),
  deleteCustomFood: (id) => apiFetch(`/api/foods/custom/${id}`, { method: "DELETE" }),
  chatHistory: () => apiFetch("/api/chat"),
  sendChat: (message) => apiFetch("/api/chat", { method: "POST", body: { message } }),
  editProposal: (id, body) => apiFetch(`/api/proposals/${id}`, { method: "PUT", body }),
  confirmProposal: (id) => apiFetch(`/api/proposals/${id}/confirm`, { method: "POST" }),
  discardProposal: (id) => apiFetch(`/api/proposals/${id}/discard`, { method: "POST" }),
  listWorkouts: () => apiFetch("/api/workouts"),
  setWorkoutStatus: (id, status) => apiFetch(`/api/workouts/${id}/status`, { method: "PUT", body: { status } }),
  listTemplates: () => apiFetch("/api/workouts/templates"),
};

export { browserTimezone };
