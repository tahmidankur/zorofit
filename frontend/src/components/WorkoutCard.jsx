import { Check } from "lucide-react";
import "./WorkoutCard.css";

const PATTERN_NAMES = {
  squat: "squat",
  hinge: "hinge",
  lunge: "lunge",
  push_horizontal: "horizontal push",
  push_vertical: "overhead push",
  pull_horizontal: "row",
  pull_vertical: "vertical pull",
  core: "core",
  carry: "carry",
};

function formatRest(seconds) {
  return seconds >= 60 && seconds % 60 === 0 ? `${seconds / 60} min rest` : `${seconds} s rest`;
}

export default function WorkoutCard({ plan, title, status, actions }) {
  return (
    <article className={`card workout-card workout-card-${status}`} aria-label={title}>
      <header className="workout-card-head">
        <div>
          <h3 className="workout-card-title">{title}</h3>
          <p className="small muted num">
            {plan.template_name} · about {plan.estimated_minutes} min
          </p>
        </div>
        {status === "done" && (
          <span className="workout-card-status">
            <Check size={16} aria-hidden="true" /> Done
          </span>
        )}
        {status === "skipped" && <span className="workout-card-status muted">Skipped</span>}
        {status === "discarded" && <span className="workout-card-status muted">Discarded</span>}
        {status === "confirmed" && <span className="workout-card-status">In use</span>}
      </header>
      <ol className="workout-list">
        {plan.exercises.map((exercise) => (
          <li key={exercise.id} className="workout-exercise">
            <span className="workout-exercise-name">{exercise.name}</span>
            <span className="small muted num">
              {exercise.sets} × {exercise.reps} · {formatRest(exercise.rest_seconds)}
            </span>
          </li>
        ))}
      </ol>
      {plan.skipped_patterns.length > 0 && (
        <p className="small muted">
          No {plan.skipped_patterns.map((p) => PATTERN_NAMES[p] ?? p).join(", ")} exercise fits your equipment.
        </p>
      )}
      {actions && <div className="btn-row">{actions}</div>}
    </article>
  );
}
