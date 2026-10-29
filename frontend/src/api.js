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

export async function apiFetch(path, { method = "GET", body } = {}) {
  const headers = {
    "X-Device-Id": getDeviceId(),
    "X-Timezone": browserTimezone(),
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(data, response.status));
  }
  return data;
}

export const api = {
  health: () => apiFetch("/api/health"),
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
};

export { browserTimezone };
