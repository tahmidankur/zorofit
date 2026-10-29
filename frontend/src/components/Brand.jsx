import { Link, useLocation } from "react-router-dom";
import wordmark from "../assets/brand/zorofit-wordmark-green.svg";
import symbol from "../assets/brand/zorofit-symbol-green.svg";
import symbolSmall from "../assets/brand/zorofit-symbol-small-green.svg";
import "./Brand.css";

export function MobileHeader() {
  // Home shows the full stacked logo, so the header wordmark would repeat it.
  if (useLocation().pathname === "/") return null;
  return (
    <header className="mobile-header">
      <Link to="/" className="brand-link" aria-label="ZoroFit home">
        <img src={wordmark} alt="" className="mobile-header-wordmark" width="81" height="28" />
      </Link>
    </header>
  );
}

export function RailLogo() {
  return (
    <Link to="/" className="brand-link rail-logo" aria-label="ZoroFit home">
      <img src={symbol} alt="" width="40" height="40" />
    </Link>
  );
}

// The kit's small-size cut stays legible at avatar size, where the full symbol's gap closes up.
export function ZoroAvatar() {
  return <img src={symbolSmall} alt="" className="zoro-avatar" width="20" height="20" />;
}
