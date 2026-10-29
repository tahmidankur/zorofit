// Long enough for the logo to register on a fast load; a slow load already showed it longer.
const MIN_VISIBLE_MS = 1100;
const FADE_MS = 450;
// Frames never come in a tab that isn't painting (opened in the background, prerendered),
// so a timer makes sure the splash still clears.
const FALLBACK_MS = 3000;

let hiding = false;

function hideSplash() {
  const splash = document.getElementById("splash");
  if (!splash || hiding) return;
  hiding = true;
  const wait = Math.max(0, MIN_VISIBLE_MS - performance.now());
  setTimeout(() => {
    splash.classList.add("splash-hidden");
    setTimeout(() => splash.remove(), FADE_MS);
  }, wait);
}

// Wait for the first paint of the app underneath, so the fade reveals a page, not a blank screen.
export function hideSplashAfterFirstPaint() {
  requestAnimationFrame(() => requestAnimationFrame(hideSplash));
  setTimeout(hideSplash, FALLBACK_MS);
}
