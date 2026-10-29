// Long enough for the logo to register on a fast load; a slow load already showed it longer.
const MIN_VISIBLE_MS = 1100;
const FADE_MS = 450;

export function hideSplash() {
  const splash = document.getElementById("splash");
  if (!splash) return;
  const wait = Math.max(0, MIN_VISIBLE_MS - performance.now());
  setTimeout(() => {
    splash.classList.add("splash-hidden");
    setTimeout(() => splash.remove(), FADE_MS);
  }, wait);
}
