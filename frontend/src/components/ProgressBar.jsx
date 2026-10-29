import { round } from "../format.js";
import "./ProgressBar.css";

export default function ProgressBar({ label, value, target, unit }) {
  const percent = target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const remaining = target - value;
  const note = remaining >= 0 ? `${round(remaining)} ${unit} left` : `${round(-remaining)} ${unit} over`;

  return (
    <div className="progress">
      <div className="progress-top">
        <span className="progress-label">{label}</span>
        <span className="progress-value num">
          ≈ {round(value)} <span className="muted">/ {round(target)} {unit}</span>
        </span>
      </div>
      <div
        className="progress-track"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={target}
        aria-valuenow={Math.round(value)}
      >
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
      <p className="progress-note small muted num">{note}</p>
    </div>
  );
}
