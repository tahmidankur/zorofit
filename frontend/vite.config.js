import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
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
});
