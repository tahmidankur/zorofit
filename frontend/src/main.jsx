import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
// Loaded before App so component stylesheets can override the shared classes.
import "./styles/global.css";
import App from "./App.jsx";
import { hideSplash } from "./splash.js";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);

// Wait for the first paint of the app underneath, so the fade reveals a page, not a blank screen.
requestAnimationFrame(() => requestAnimationFrame(hideSplash));
