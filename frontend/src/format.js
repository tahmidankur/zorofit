const whole = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

export function round(value) {
  return whole.format(value);
}

export function formatKcal(value) {
  return `≈ ${round(value)} kcal`;
}

export function parseLocalDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function formatDay(isoDate) {
  return parseLocalDate(isoDate).toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export function formatTime(isoDatetime) {
  return new Date(isoDatetime).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function pad(value) {
  return String(value).padStart(2, "0");
}

export function toLocalInputValue(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function capitalize(text) {
  return text ? text[0].toUpperCase() + text.slice(1) : "";
}
