import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
// Loaded before App so component stylesheets can override the shared classes.
import "./styles/global.css";
import App from "./App.jsx";
import { hideSplashAfterFirstPaint } from "./splash.js";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);

hideSplashAfterFirstPaint();
