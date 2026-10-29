const STORAGE_KEY = "zoro.deviceId";

// crypto.randomUUID only exists in secure contexts, so a phone opening the dev
// server over a LAN address (plain http) needs the getRandomValues fallback.
function newUuid() {
  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function getDeviceId() {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = newUuid();
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}
