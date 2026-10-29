import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// The device id in localStorage is the user's only credential, so the built page may run scripts
// from its own origin only and talk to nothing but itself and the API. Dev is left alone because
// Vite's hot reload needs inline scripts.
function contentSecurityPolicy(apiUrl) {
  const apiOrigin = new URL(apiUrl).origin;
  const policy = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    `connect-src 'self' ${apiOrigin}`,
    "manifest-src 'self'",
    "worker-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
  return {
    name: "content-security-policy",
    apply: "build",
    transformIndexHtml: (html) =>
      html.replace("<head>", `<head>\n    <meta http-equiv="Content-Security-Policy" content="${policy}" />`),
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiUrl = env.VITE_API_URL || "http://localhost:8000";
  return {
    plugins: [
      react(),
      contentSecurityPolicy(apiUrl),
      VitePWA({
        registerType: "autoUpdate",
        includeAssets: ["favicon.ico", "icons/favicon.svg", "icons/apple-touch-icon.png"],
        manifest: {
          name: "ZoroFit",
          short_name: "ZoroFit",
          description: "Log meals and plan workouts by chatting with Zoro.",
          start_url: "/",
          scope: "/",
          display: "standalone",
          orientation: "portrait",
          // Zoro Green behind the launch icon matches the in-app splash, so launch reads as one screen.
          theme_color: "#0E6B47",
          background_color: "#0E6B47",
          icons: [
            { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
            { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
            { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
          ],
        },
        workbox: {
          // The app is a single page; any route offline should open the cached shell.
          navigateFallback: "/index.html",
          globPatterns: ["**/*.{js,css,html,svg,png,ico}"],
        },
      }),
    ],
  };
});
