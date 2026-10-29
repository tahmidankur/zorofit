import { Link } from "react-router-dom";
import wordmark from "../assets/brand/zorofit-wordmark-green.svg";
import symbol from "../assets/brand/zorofit-symbol-green.svg";
import symbolSmall from "../assets/brand/zorofit-symbol-small-green.svg";
import "./Brand.css";

export function MobileHeader() {
  return (
    <header className="mobile-header">
      <Link to="/today" className="brand-link" aria-label="ZoroFit, go to Today">
        <img src={wordmark} alt="" className="mobile-header-wordmark" width="81" height="28" />
      </Link>
    </header>
  );
}

export function RailLogo() {
  return (
    <Link to="/today" className="brand-link rail-logo" aria-label="ZoroFit, go to Today">
      <img src={symbol} alt="" width="40" height="40" />
    </Link>
  );
}

// The kit's small-size cut stays legible at avatar size, where the full symbol's gap closes up.
export function ZoroAvatar() {
  return <img src={symbolSmall} alt="" className="zoro-avatar" width="20" height="20" />;
}
